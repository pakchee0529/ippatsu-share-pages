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

## Part B — 修正案 JSON API（Web アプリ案・未デプロイ）

**目的**

- 回答スプレッドシートから **最新の修正案** を JSON で返す。
- ポータル（将来）が `fetch` で読み、**表示だけ**上書きする。

**返却 JSON 案**

```json
{
  "ok": true,
  "edits": [
    {
      "id": "...",
      "timestamp": "...",
      "date": "260514",
      "management_no": "...",
      "management_no_key": "...",
      "label": "...",
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

**集約ルール（案）**

- 同一 `date` + `management_no`（または `management_no_key`）の複数行がある場合は **タイムスタンプ最新を優先**。

**簡易 token 認証（案）**

- スクリプトプロパティ `API_TOKEN` を設定（**本番前に必ず差し替え**）。
- リクエスト `?token=...` または `Authorization: Bearer ...` で一致しなければ `{"ok":false,"error":"unauthorized"}`。

```javascript
// --- 設定: スクリプトプロパティ API_TOKEN を設定すること（プレースホルダ） ---
// File → Project settings → Script properties → API_TOKEN = （ランダム文字列）

function doGet(e) {
  const token = (e && e.parameter && e.parameter.token) || '';
  const expected = PropertiesService.getScriptProperties().getProperty('API_TOKEN');
  // TODO: 本番では constant-time 比較など検討
  if (!expected || token !== expected) {
    return ContentService.createTextOutput(
      JSON.stringify({ ok: false, error: 'unauthorized' })
    ).setMimeType(ContentService.MimeType.JSON);
  }

  // TODO: 回答シートを開き、ヘッダ行に合わせて行をパースし、edits 配列を構築
  const edits = [];

  return ContentService.createTextOutput(
    JSON.stringify({ ok: true, edits: edits })
  ).setMimeType(ContentService.MimeType.JSON);
}
```

**Web アプリ URL の取得手順**

1. Apps Script エディタで **デプロイ** → **新しいデプロイ** → 種類「ウェブアプリ」。
2. 次を実行するユーザー: **自分**、アクセスできるユーザー: **全員（匿名含む）** または社内のみ（要件に合わせる）。
3. デプロイ後に表示される **ウェブアプリ URL** を控える（ポータル側の `fetch` 先・将来）。

**セキュリティ**

- `API_TOKEN` は **スクリプトプロパティ** にのみ保存し、リポジトリにコミットしない。
- スプレッドシート ID もコード直書きせず、プロパティ推奨。
