# 現場共有「詳細修正報告」— Google Apps Script メモ

このファイルは **リポジトリ内のメモ／ひな形**です。Google のスクリプトエディタにコピーして実行・デプロイしてください。

## Part A — フォーム「現場共有 詳細修正報告」の作成

**目的**

- フォームと回答用スプレッドシートを自動作成する。
- 事前入力用 URL のたたき台をログに出す（**実際の entry ID は実行後ログで確認し、`generate_portal.py` の定数へ反映**）。

**フォーム項目（報告者なし）**

| 質問タイトル   | 備考 |
|----------------|------|
| 対象日付       | 短文（例: 6桁 `260514`） |
| 管理番号       |      |
| 径間名         |      |
| 処理方法       |      |
| B車            |      |
| 道幅           |      |
| 傾斜           | 正本に無い場合はフォームから省略してよい |
| 枝切り本数     |      |
| 根切り本数     |      |
| 柴面積         |      |
| 竹本数         |      |
| つる箇所数     |      |
| 警告           | 段落 |
| 備考           | 段落 |
| 修正メモ       | 段落 |

```javascript
/**
 * 一度だけ実行: フォーム + 回答スプレッドシート作成し、prefill 用 URL の骨格をログ出力する。
 * 実行後、ログに出た entry.XXXXXXXX を控え、ippatsu-share-pages の generate_portal.py 定数へ転記する。
 */
function createShareDetailEditForm_() {
  const form = FormApp.create('現場共有 詳細修正報告');
  form.setDescription('現場共有ページの詳細項目の修正を報告します。採用は会社側で判断します。');
  form.setCollectEmail(false);

  const items = [
    ['対象日付', FormApp.ItemType.TEXT],
    ['管理番号', FormApp.ItemType.TEXT],
    ['径間名', FormApp.ItemType.TEXT],
    ['処理方法', FormApp.ItemType.TEXT],
    ['B車', FormApp.ItemType.TEXT],
    ['道幅', FormApp.ItemType.TEXT],
    ['傾斜', FormApp.ItemType.TEXT],
    ['枝切り本数', FormApp.ItemType.TEXT],
    ['根切り本数', FormApp.ItemType.TEXT],
    ['柴面積', FormApp.ItemType.TEXT],
    ['竹本数', FormApp.ItemType.TEXT],
    ['つる箇所数', FormApp.ItemType.TEXT],
    ['警告', FormApp.ItemType.PARAGRAPH_TEXT],
    ['備考', FormApp.ItemType.PARAGRAPH_TEXT],
    ['修正メモ', FormApp.ItemType.PARAGRAPH_TEXT],
  ];

  const entryIds = [];
  for (const [title, type] of items) {
    let q;
    if (type === FormApp.ItemType.PARAGRAPH_TEXT) {
      q = form.addParagraphTextItem();
    } else {
      q = form.addTextItem();
    }
    q.setTitle(title).setRequired(false);
    entryIds.push({ title: title, id: q.getId() });
  }

  const ss = SpreadsheetApp.create('Responses_現場共有_詳細修正報告');
  form.setDestination(FormApp.DestinationType.SPREADSHEET, ss.getId());

  const publishedUrl = form.getPublishedUrl();
  const formId = form.getId();
  Logger.log('FORM_ID=' + formId);
  Logger.log('RESPONSE_SPREADSHEET_ID=' + ss.getId());
  Logger.log('PUBLISHED_URL=' + publishedUrl);
  Logger.log('EDIT_URL=' + form.getEditUrl());

  Logger.log('--- 各質問の item ID（多くの場合 prefill の entry.xxx と一致。不一致時はフォームの「事前入力した URL を取得」で確認）---');
  entryIds.forEach(function (row) {
    Logger.log(row.title + '\titemId=' + row.id);
  });
  Logger.log('Googleフォーム編集画面 → ⋮ → 「事前入力した URL を取得」で entry.YYYY を確認し、generate_portal.py の SHARE_DETAIL_EDIT_ENTRY_* に設定してください。');
}
```

**注意（Google の仕様）**

- `FormApp.create` 直後の「回答用 URL」は、公開用の `/d/e/<formKey>/viewform` 形式と **formId が一致しない場合**があります。**事前入力した URL を取得** から正式な `entry.xxxxx` をコピーするのが確実です。

---

## Part B — 修正案 JSON API（Web アプリ・貼り付け用コード）

**目的**

- フォーム回答スプレッドシートを読み、**未確定修正**を JSON で返す。
- 現場共有ページ（静的 HTML）が `fetch` で読み、**表示だけ**上書きする（正本 JSON は変更しない）。

**返却 JSON 形式（成功時）**

```json
{
  "ok": true,
  "edits": [
    {
      "id": "12",
      "timestamp": "2026-05-15T04:12:34.567Z",
      "date": "260515",
      "management_no": "514 07316",
      "management_no_key": "51407316",
      "label": "古山野18〜19",
      "fields": {
        "work_method": "...",
        "bucket_truck": "...",
        "road_width": "...",
        "slope": "...",
        "branch_count": "...",
        "root_count": "...",
        "bush_area": "...",
        "bamboo_count": "...",
        "vine_count": "...",
        "warning": "...",
        "note": "..."
      },
      "edit_note": "..."
    }
  ]
}
```

**認証**

- クエリ `?token=...` を検証し、一致しない場合は `{"ok":false,"error":"unauthorized"}` を返す。
- **推奨:** スクリプトプロパティ `API_TOKEN` にトークンを保存（リポジトリに載せない）。
- **初回のみ:** 下記 `API_TOKEN_FALLBACK` をコード上で差し替えてもよい（本番前に必ずプロパティへ移すこと）。

**集約ルール**

- 同一 `date` + `management_no_key`（空白除去後の管理番号）に複数行ある場合は、**タイムスタンプ列が新しい行を優先**して 1 件だけ `edits` に含める。

**スプレッドシート前提**

- 1 行目はヘッダ。Google フォーム連携の回答シートでは、先頭列が **タイムスタンプ**（日本語環境では `タイムスタンプ`）のことが多い。
- 次の質問タイトルと **完全一致** で列を特定する（列順が変わっても動く）:

| ヘッダ文字列（1 行目） |
|------------------------|
| 対象日付 |
| 管理番号 |
| 径間名 |
| 処理方法 |
| B車 |
| 道幅 |
| 傾斜 |
| 枝切り本数 |
| 根切り本数 |
| 柴面積 |
| 竹本数 |
| つる箇所数 |
| 警告 |
| 備考 |
| 修正メモ |

**セットアップ手順**

1. 下記コードを Apps Script プロジェクトに貼り付ける。
2. **プロジェクトの設定 → スクリプトのプロパティ** に以下を追加（推奨）:
   - `API_TOKEN` … 共有ページ `SHARE_DETAIL_EDIT_API_TOKEN` と同じ文字列。
   - `RESPONSE_SPREADSHEET_ID` … 回答スプレッドシートの ID（URL の `/d/` と `/edit` の間）。
3. またはコード内の `API_TOKEN_FALLBACK` / `RESPONSE_SPREADSHEET_ID_FALLBACK` を一時的に埋める（本番はプロパティ推奨）。
4. **デプロイ → 新しいデプロイ → 種類: ウェブアプリ**  
   - 次のユーザーとして実行: **自分**  
   - アクセスできるユーザー: **全員**（GitHub Pages 等の静的サイトから `fetch` する場合）または社内のみ。
5. 表示された **ウェブアプリ URL** を `generate_portal.py` の `SHARE_DETAIL_EDIT_API_URL` に設定し、`python scripts/generate_portal.py` で共有 HTML を再生成する。

**セキュリティ**

- トークンは URL クエリに載るため、HTTPS のみで運用し、トークンは十分長いランダム文字列にする。
- スプレッドシート ID はリポジトリにコミットしない（プロパティ推奨）。

### Apps Script 全文（`Code.gs` 用）

```javascript
/**
 * 現場共有「詳細修正報告」回答 → JSON API（doGet）
 *
 * 設定（優先順）:
 *   スクリプトプロパティ API_TOKEN
 *   スクリプトプロパティ RESPONSE_SPREADSHEET_ID
 * 未設定時は下の FALLBACK 定数（差し替え用）
 */

/** @const 本番ではスクリプトプロパティ API_TOKEN を必ず設定してください */
var API_TOKEN_FALLBACK = 'REPLACE_ME';

/** @const 本番ではスクリプトプロパティ RESPONSE_SPREADSHEET_ID を必ず設定してください */
var RESPONSE_SPREADSHEET_ID_FALLBACK = 'REPLACE_SPREADSHEET_ID';

var HEADER_NAMES = {
  ts: ['タイムスタンプ', 'Timestamp'],
  date: ['対象日付'],
  management_no: ['管理番号'],
  label: ['径間名'],
  work_method: ['処理方法'],
  bucket_truck: ['B車'],
  road_width: ['道幅'],
  slope: ['傾斜'],
  branch_count: ['枝切り本数'],
  root_count: ['根切り本数'],
  bush_area: ['柴面積'],
  bamboo_count: ['竹本数'],
  vine_count: ['つる箇所数'],
  warning: ['警告'],
  note: ['備考'],
  edit_note: ['修正メモ'],
};

function jsonOut_(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj)).setMimeType(ContentService.MimeType.JSON);
}

function getProp_(key) {
  return PropertiesService.getScriptProperties().getProperty(key) || '';
}

function colIndex_(headerRow, candidates) {
  var h = headerRow.map(function (cell) {
    return String(cell == null ? '' : cell).trim();
  });
  for (var c = 0; c < candidates.length; c++) {
    var name = candidates[c];
    for (var i = 0; i < h.length; i++) {
      if (h[i] === name) return i;
    }
  }
  return -1;
}

function tsIndex_(headerRow) {
  var idx = colIndex_(headerRow, HEADER_NAMES.ts);
  if (idx >= 0) return idx;
  return 0;
}

function cellStr_(row, idx) {
  if (idx < 0 || idx >= row.length) return '';
  var v = row[idx];
  if (v instanceof Date) {
    return v.toISOString ? v.toISOString() : String(v);
  }
  return String(v == null ? '' : v);
}

function rowTimeMs_(row, tsIdx) {
  var v = row[tsIdx];
  if (v instanceof Date) return v.getTime();
  return 0;
}

function normMgmtKey_(s) {
  return String(s == null ? '' : s).replace(/\s+/g, '');
}

function doGet(e) {
  var token = (e && e.parameter && e.parameter.token) || '';
  var expected = getProp_('API_TOKEN') || API_TOKEN_FALLBACK;
  if (!expected || token !== expected) {
    return jsonOut_({ ok: false, error: 'unauthorized' });
  }

  var ssId = getProp_('RESPONSE_SPREADSHEET_ID') || RESPONSE_SPREADSHEET_ID_FALLBACK;
  if (!ssId || ssId === 'REPLACE_SPREADSHEET_ID') {
    return jsonOut_({ ok: false, error: 'config', detail: 'RESPONSE_SPREADSHEET_ID missing' });
  }

  var ss;
  try {
    ss = SpreadsheetApp.openById(ssId);
  } catch (err) {
    return jsonOut_({ ok: false, error: 'spreadsheet', detail: String(err) });
  }

  var sh = ss.getSheets()[0];
  var range = sh.getDataRange();
  var values = range.getValues();
  if (!values || values.length < 2) {
    return jsonOut_({ ok: true, edits: [] });
  }

  var header = values[0];
  var tsIdx = tsIndex_(header);
  var ci = {
    date: colIndex_(header, HEADER_NAMES.date),
    management_no: colIndex_(header, HEADER_NAMES.management_no),
    label: colIndex_(header, HEADER_NAMES.label),
    work_method: colIndex_(header, HEADER_NAMES.work_method),
    bucket_truck: colIndex_(header, HEADER_NAMES.bucket_truck),
    road_width: colIndex_(header, HEADER_NAMES.road_width),
    slope: colIndex_(header, HEADER_NAMES.slope),
    branch_count: colIndex_(header, HEADER_NAMES.branch_count),
    root_count: colIndex_(header, HEADER_NAMES.root_count),
    bush_area: colIndex_(header, HEADER_NAMES.bush_area),
    bamboo_count: colIndex_(header, HEADER_NAMES.bamboo_count),
    vine_count: colIndex_(header, HEADER_NAMES.vine_count),
    warning: colIndex_(header, HEADER_NAMES.warning),
    note: colIndex_(header, HEADER_NAMES.note),
    edit_note: colIndex_(header, HEADER_NAMES.edit_note),
  };

  if (ci.date < 0 || ci.management_no < 0) {
    return jsonOut_({ ok: false, error: 'header', detail: 'Need columns 対象日付 and 管理番号' });
  }

  var rows = [];
  for (var r = 1; r < values.length; r++) {
    rows.push({ sheetRow: r + 1, row: values[r] });
  }
  rows.sort(function (a, b) {
    return rowTimeMs_(b.row, tsIdx) - rowTimeMs_(a.row, tsIdx);
  });

  var picked = {};
  var edits = [];

  for (var i = 0; i < rows.length; i++) {
    var row = rows[i].row;
    var date = cellStr_(row, ci.date).trim();
    var management_no = cellStr_(row, ci.management_no).trim();
    var key = normMgmtKey_(management_no);
    if (!date || !key) continue;
    var dedupeKey = date + '\t' + key;
    if (picked[dedupeKey]) continue;
    picked[dedupeKey] = true;

    var tsIso = cellStr_(row, tsIdx);
    var fields = {};
    if (ci.work_method >= 0) fields.work_method = cellStr_(row, ci.work_method);
    if (ci.bucket_truck >= 0) fields.bucket_truck = cellStr_(row, ci.bucket_truck);
    if (ci.road_width >= 0) fields.road_width = cellStr_(row, ci.road_width);
    if (ci.slope >= 0) fields.slope = cellStr_(row, ci.slope);
    if (ci.branch_count >= 0) fields.branch_count = cellStr_(row, ci.branch_count);
    if (ci.root_count >= 0) fields.root_count = cellStr_(row, ci.root_count);
    if (ci.bush_area >= 0) fields.bush_area = cellStr_(row, ci.bush_area);
    if (ci.bamboo_count >= 0) fields.bamboo_count = cellStr_(row, ci.bamboo_count);
    if (ci.vine_count >= 0) fields.vine_count = cellStr_(row, ci.vine_count);
    if (ci.warning >= 0) fields.warning = cellStr_(row, ci.warning);
    if (ci.note >= 0) fields.note = cellStr_(row, ci.note);

    var edit_note = ci.edit_note >= 0 ? cellStr_(row, ci.edit_note) : '';

    edits.push({
      id: String(rows[i].sheetRow),
      timestamp: tsIso,
      date: date,
      management_no: management_no,
      management_no_key: key,
      label: ci.label >= 0 ? cellStr_(row, ci.label) : '',
      fields: fields,
      edit_note: edit_note,
    });
  }

  return jsonOut_({ ok: true, edits: edits });
}
```

**動作確認（ブラウザ）**

```
https://script.google.com/macros/s/XXXX/exec?token=あなたのAPI_TOKEN
```

`ok:true` と `edits` が返れば共有ページ側と接続可能です。
