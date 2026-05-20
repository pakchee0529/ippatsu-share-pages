# 現場共有 詳細修正フォーム V2化・ライブ未確定修正対応 作業ログ

このドキュメントは **実装の引き継ぎ・再検証用** の作業記録です。コード仕様の要約ではなく、次回この作業を再開するときに必要な情報をできるだけ省略せず載せています。

---

## 1. 作業テーマ

**タイトル:** 現場共有 詳細修正フォーム V2化・ライブ未確定修正対応 作業ログ

**今回の主目的**

- 現場共有ページの各カードから、現場側がスマホや PC で詳細内容を修正できるようにする。
- Google フォームで詳細修正を送信し、Apps Script API 経由で共有ページに **未確定修正** として反映する。
- 旧フォームで枝切り・根切りが **総数入力** になっていた問題を是正する。
- PC 版いっぱつちゃんの **正本データと同じ、枝切り・根切り 6 区分** に合わせる。
- **`warning` / `edit_note` / `branch_count` / `root_count`** を V2 フォーム運用から外す。

---

## 2. 最終到達点

以下の流れが成立した状態を記録する。

```
現場共有ページ
  ↓ 現場指示を開く
「詳細を修正」ボタン
  ↓
Google フォーム V2「現場共有 詳細修正」
  ↓ 枝切り・根切りを 6 区分で送信
V2 回答スプレッドシートへ保存
  ↓
Apps Script JSONP API が V2 形式で返却
  ↓
共有ページ側が未確定修正として反映可能
```

**V2 API 確認で、旧形式の以下が消えた（返却に含めない）**

- `branch_count`
- `root_count`
- `warning`
- `edit_note`

**V2 API 確認で、以下の 12 区分キーが返ることを確認済み**

| 枝切りキー | 根切りキー |
|------------|------------|
| `branch_cut_under_10` | `root_cut_under_10` |
| `branch_cut_10_20` | `root_cut_10_20` |
| `branch_cut_20_30` | `root_cut_20_30` |
| `branch_cut_30_40` | `root_cut_30_40` |
| `branch_cut_40_50` | `root_cut_40_50` |
| `branch_cut_over_50` | `root_cut_over_50` |

---

## 3. 共有ページ側の詳細修正導線

**当初**

- 「詳細修正を報告」ボタンがカード上部に大きく表示されていた。
- 使用頻度が低い割に目立ちすぎていた。

**変更後**

- カード上部には **「地図」「2 点地図」「現場指示」** のみ。
- 詳細修正導線は **「現場指示」パネルの一番下** に移動。
- ボタン文言を **「詳細修正を報告」→「詳細を修正」** に変更。
- 説明文「現地で内容が違う場合のみ修正報告してください。」は **削除**。
- ボタンだけを控えめに表示。**スマホで押せるタップサイズ（min-height 44px など）は維持**。

**方針として記録すること**

- 詳細修正は **通常導線ではなく、現場指示の奥** に置く。
- 使用頻度が低く、現場作業時の邪魔にならないようにした。

---

## 4. fetch から JSONP への変更

**問題**

GitHub Pages から Apps Script Web アプリへ `fetch` したところ、CORS で失敗した。

**Console で確認したエラー（例）**

```text
Access to fetch at script.google.com ... from origin github.io has been blocked by CORS policy
```

**理由**

- `fetch()` はクロスオリジンで `Access-Control-Allow-Origin` が必要。
- Apps Script Web アプリは、このヘッダを都合よく返せないケースがある。
- ブラウザで直接 API URL を開くと JSON は返るが、GitHub Pages からの `fetch` はブロックされる。

**対応**

- `fetch()` を廃止し、**JSONP** に変更。
- 共有ページ側から `<script src="...">` で Apps Script API を読み込む。
- API URL に **`callback`** を付ける。
- Apps Script 側は **`callback({...});`** を返す（`MimeType.JAVASCRIPT`）。
- JSONP は script として読み込むため **CORS 制約を回避**できる。

**JSONP 確認 URL（例）**

```text
https://script.google.com/macros/s/AKfycbzLtv-yZP5QNjXQSEybhxBTmWrNaujJJfyb_okMcuSzjKyREFthJTwI_Y5fc0PKfGuOnA/exec?token=ippatsu_share_detail_edit_202605_long_token&callback=testCb
```

**成功時の形式**

```text
testCb({"ok":true,"edits":[...]});
```

---

## 5. スマホ反映問題

**現象**

PC では未確定修正表示に成功したが、スマホでは表示されないケースがあった。

**入れた対策（共有ページ側ライブ編集インジェクション）**

- JSONP URL に **`_ts=Date.now()`** のキャッシュバスター追加。
- **`DOMContentLoaded`** 後に **`requestAnimationFrame`** で実行。
- `<script>` 挿入先を **`document.head` 以外にもフォールバック**。
- **callback cleanup を遅延**。
- **`[share-live-edit]`** の console **info / warn を強化**。

**現時点の扱い**

- スマホでの未表示は **深追いせず保留**。
- API / JSONP / PC 表示は成功。**現場側からフォーム送信できることを優先**。
- 将来必要なら **スマホ実機** で JSONP 読み込み・キャッシュ・Safari / Chrome 差を検証する。

---

## 6. 枝切り・根切り表示の復旧

**一時的な問題**

共有ページの枝切り・根切りが、6 区分ではなく **総数表示のよう** に見えた。

**原因**

- `ippatsu-share-pages/scripts/generate_portal.py` 内のライブ編集 JS で **`applyCutTotals`** が、未確定修正適用時に `.instr-cut tbody` を **不適切に扱い**、結果として **6 区分行が失われる** 事象があった（総数 1 行のみ・「合計（未確定修正）」だけに見える状態）。
- prefill 側も枝・根を **総数扱い** にしていた期間があった。

**修正方針（実装済みの考え方）**

- **6 区分行は残す**（削除しない）。
- 未確定での **総数のみ** の表現が必要な legacy 時は、**`tr.instr-cut-pending-total`** を末尾に追加。
- **`instr-cut-total` / `instr-cut-pending-total`** は **prefill 集計対象に含めない**。
- PC 側 `html_generator.py`（`ippatsu-pc`）では **6 区分＋静的合計行** を表示。
- ライブ編集 V2 では、**12 区分キー**が来た場合に **該当セルだけ上書き**。
- **静的合計行**（`tr.instr-cut-total`）がある場合、上書き後に **合計を再計算**。

---

## 7. 枝切り・根切りの正本 JSON キー

| 区分 | 枝切り JSON キー | 根切り JSON キー |
|------|------------------|------------------|
| 〜10 未満 | `branch_cut_under_10` | `root_cut_under_10` |
| 〜20 未満 | `branch_cut_10_20` | `root_cut_10_20` |
| 〜30 未満 | `branch_cut_20_30` | `root_cut_20_30` |
| 〜40 未満 | `branch_cut_30_40` | `root_cut_30_40` |
| 〜50 未満 | `branch_cut_40_50` | `root_cut_40_50` |
| 50 以上 | `branch_cut_over_50` | `root_cut_over_50` |

**補足**

- **flat key** が正本。
- 旧 `branch_cuts` / `root_cuts` の **6 要素配列**は **移行互換用**。
- flat に非ゼロがあれば **flat 優先**。
- flat が全ゼロで配列のみ実データの場合に **配列から 6 区分へ展開**。

---

## 8. Google フォーム V2

| 項目 | 値 |
|------|-----|
| 旧フォーム名 | 現場共有 詳細修正報告 |
| 新フォーム名 | 現場共有 詳細修正 |
| 新フォーム URL（回答） | `https://docs.google.com/forms/d/e/1FAIpQLSftmxlaA3vwt1s-AT7MOia5hHy3dtL5vbcsvgZHUinq9ETRQg/viewform` |
| 編集 URL | `https://docs.google.com/forms/d/1-PkJTyq4E0CV_VE77xUkCUeTjBhHkxsZQN5SHs3akzQ/edit` |
| V2 回答スプレッドシート URL | `https://docs.google.com/spreadsheets/d/1LyzdIpbgDiEo02A8FkTx2FyR2ROStpIOBU8kNNdxt68/edit` |
| V2 回答スプレッドシート ID | `1LyzdIpbgDiEo02A8FkTx2FyR2ROStpIOBU8kNNdxt68` |

---

## 9. V2 フォーム項目

### 基本情報

- 対象日付
- 管理番号
- 径間名

### 処理・条件

**処理方法**

- 持出
- 集積
- 持出・集積

**B 車**

- 可
- 一部可能
- 不可

**傾斜**

- 平
- 傾
- 崖

**その他**

- 道幅

### 枝切り 6 区分

- 枝切り 〜10 未満
- 枝切り 〜20 未満
- 枝切り 〜30 未満
- 枝切り 〜40 未満
- 枝切り 〜50 未満
- 枝切り 50 以上

### 根切り 6 区分

- 根切り 〜10 未満
- 根切り 〜20 未満
- 根切り 〜30 未満
- 根切り 〜40 未満
- 根切り 〜50 未満
- 根切り 50 以上

### その他伐採

- 柴伐採面積
- 竹伐採本数
- つる伐採箇所数

### 備考

- 備考

---

## 10. V2 で削除・廃止した項目

**V2 フォームから外したもの**

- 警告
- 修正メモ
- 枝切り本数（総数）
- 根切り本数（総数）
- 報告者

**理由**

- `warning` は PC 版入力項目ではなく、自動生成の補助表示。
- `edit_note` は正本外のライブ編集 API 用メモ。
- `branch_count` / `root_count` は 6 区分から計算できる派生値で、**逆変換できない**。
- 報告者は今回の用途では不要。

---

## 11. V2 entry ID 対応表

**フォーム URL（回答）**

`https://docs.google.com/forms/d/e/1FAIpQLSftmxlaA3vwt1s-AT7MOia5hHy3dtL5vbcsvgZHUinq9ETRQg/viewform`

| 項目 | entry ID |
|------|----------|
| 対象日付 | `entry.1582884252` |
| 管理番号 | `entry.2102936974` |
| 径間名 | `entry.932009684` |
| 処理方法 | `entry.579262382` |
| B 車 | `entry.2099732396` |
| 道幅 | `entry.1713335536` |
| 傾斜 | `entry.539982619` |
| 枝切り 〜10 未満 | `entry.948358914` |
| 枝切り 〜20 未満 | `entry.740813394` |
| 枝切り 〜30 未満 | `entry.74377314` |
| 枝切り 〜40 未満 | `entry.957344080` |
| 枝切り 〜50 未満 | `entry.382023163` |
| 枝切り 50 以上 | `entry.288483164` |
| 根切り 〜10 未満 | `entry.1467113295` |
| 根切り 〜20 未満 | `entry.108281366` |
| 根切り 〜30 未満 | `entry.77416071` |
| 根切り 〜40 未満 | `entry.792549802` |
| 根切り 〜50 未満 | `entry.1363589096` |
| 根切り 50 以上 | `entry.388844699` |
| 柴伐採面積 | `entry.133683289` |
| 竹伐採本数 | `entry.1908811234` |
| つる伐採箇所数 | `entry.1406858047` |
| 備考 | `entry.1367667439` |

**コード上の定数名（参考・`generate_portal.py`）**

- `SHARE_DETAIL_EDIT_ENTRY_*` が上記に対応。総数用 `SHARE_DETAIL_EDIT_ENTRY_BRANCH_COUNT` / `ROOT_COUNT` および warning / edit_note 用 entry は **V2 では使わない**。

---

## 12. Apps Script 側の状態

**前提メモ**

- 途中で **別の Apps Script プロジェクト**を触っていた可能性があった。
- 最終的には **正しいプロジェクト**で再デプロイできた、と記録する。

**正しい Web アプリ URL（API）**

`https://script.google.com/macros/s/AKfycbzLtv-yZP5QNjXQSEybhxBTmWrNaujJJfyb_okMcuSzjKyREFthJTwI_Y5fc0PKfGuOnA/exec`

**トークン（共有ページ・クエリ用）**

`ippatsu_share_detail_edit_202605_long_token`

**確認済み（運用時のチェックリスト）**

- `HEADER_NAMES` が `branch_cut_*` / `root_cut_*` の **12 区分**になっている。
- `branch_count` / `root_count` / `warning` / `edit_note` は **API 返却から消えた**。
- `RESPONSE_SPREADSHEET_ID_FALLBACK`（ドキュメント上のフォールバック）は **V2 の ID**。
- スクリプトプロパティ **`RESPONSE_SPREADSHEET_ID`** も **V2 の ID** に設定。
- 既存 Web アプリを **新バージョンで再デプロイ済み**。

**注意**

- 旧フォーム作成関数が Apps Script 内に残っていても、**実行しなければ問題なし**。
- 重要なのは **`doGet(e)` が V2 API** になっていること。

**リポジトリ内のひな形**

- `ippatsu-share-pages/docs/share_detail_edit_form_apps_script.md` の **Part B** が V2 向けに更新済み（貼り付け・再デプロイの参照用）。

---

## 13. V2 API 動作確認

**最終確認レスポンス（JSONP・1 行・実例）**

```text
testCb({"ok":true,"edits":[{"id":"2","timestamp":"2026-05-16T02:41:05.615Z","date":"260518","management_no":"514 02889","management_no_key":"51402889","label":"葛川25～26","fields":{"work_method":"集積","bucket_truck":"不可","road_width":"0m","slope":"傾","branch_cut_under_10":"0","branch_cut_10_20":"2","branch_cut_20_30":"6","branch_cut_30_40":"1","branch_cut_40_50":"1","branch_cut_over_50":"99","root_cut_under_10":"5","root_cut_10_20":"7","root_cut_20_30":"3","root_cut_30_40":"0","root_cut_40_50":"0","root_cut_over_50":"0","bush_area":"0㎡","bamboo_count":"0本","vine_count":"0箇所","note":"備考 谷越 2班に別れて。25側750チル。クローラー、一輪車、ショイコ、チルx1、ロープx2"}}]});
```

**このレスポンスにより確認済み**

- `edit_note` なし
- `warning` なし
- `branch_count` / `root_count` なし
- `branch_cut_*` あり
- `root_cut_*` あり
- **JSONP 形式**で返却成功

---

## 14. Git / リポジトリ作業

### 14.1 ippatsu-share-pages

**主要コミット**

- `23656e3` — `Switch detail edit form to size-band fields`

**このコミットで実施された内容（記録）**

- V2 フォーム URL へ差し替え。
- V2 entry ID へ差し替え。
- prefill を枝切り/根切り **総数 → 12 区分**へ変更。
- `warning` / `edit_note` / `branch_count` / `root_count` を **V2 フォーム prefill URL から除外**。
- Apps Script Part B ドキュメント（`docs/share_detail_edit_form_apps_script.md`）を **V2 対応**。
- ライブ編集 JS を **6 区分反映**へ変更。
- 共有ページ **7 本**を再生成。

**再生成対象（共有ページ）**

- `share/260518/index.html`
- `share/260519/index.html`
- `share/260520/index.html`
- `share/260521/index.html`
- `share/260522/index.html`
- `share/260525/index.html`
- `share/261231/index.html`

**不要差分（コミット対象外として戻した）**

- `portal/survey/index.html`
- `portal/archive/**`

（`generate_portal.py` 実行でこれらも更新されることがあるため、**明示的に checkout で戻してから** 対象ファイルだけ commit した、という運用。）

### 14.2 ippatsu-pc

**主要コミット（別リポジトリ）**

- `f2545dc` — `Restore size-based cut counts in share pages`

**内容（記録）**

- `html_generator.py` 側で枝切り・根切り **6 区分＋合計行**表示。
- `generate_share_from_json.py` 側で旧 `branch_cuts` / `root_cuts` 配列互換。
- `docs/share_detail_edit_form_field_map.md` 新規作成。
- `docs/share_mode_design.md` に参照追加。

---

## 15. 既知の注意点

### 15.1 スマホで未確定修正が出ない件

PC では表示成功していたが、スマホでは出ないケースあり。**現時点では深追いせず保留。**

理由:

- API / JSONP / PC 表示は成功。
- 実務上、スマホで未確定反映が即表示されなくても致命的ではない想定。
- 現場側から **フォーム送信できること**を優先。

### 15.2 旧フォーム作成関数

Apps Script 内に旧フォーム作成関数が残っている可能性あり。

扱い:

- **実行しなければ問題なし**。
- 不安なら後日整理。
- 今回は動いている **`doGet(e)`** を優先。

### 15.3 legacy `branch_count` / `root_count`

`generate_portal.py` 側では、旧 API 互換として **`branch_count` / `root_count` が来た場合** に pending total 行を出す処理が **残っている**。

扱い:

- V2 フォームからは送らない。
- **legacy 互換**として残す。
- 将来不要になれば削除候補。

### 15.4 古い未確定回答

旧フォーム回答は **旧スプレッドシート側**に残っている。

扱い:

- V2 API は **V2 回答スプレッドシート**を参照するため、旧回答は基本的に見ない。
- 必要なら旧フォーム・旧シートは後日アーカイブ扱いにする。

---

## 16. 次に確認するとよいこと

1. 公開共有ページを開く:  
   `https://pakchee0529.github.io/ippatsu-share-pages/share/260518/`

2. **対象カード**
   - 径間名: 葛川 25〜26
   - 管理番号: 514 02889

3. **期待する表示**
   - 「現場修正あり（未確定）」（および会社確認前バナー）
   - 枝切り **50 以上 = 99**（上記テスト送信に基づく場合）
   - 枝切り・根切りの **6 区分表が潰れていない**
   - **合計行**が再計算されている（`instr-cut-total` があるページ構成の場合）

4. 「詳細を修正」から **V2 フォーム**へ遷移すること。

5. prefill で **枝切り・根切り 6 区分**が入ること（合計行・pending 行の値が混ざらないこと）。

---

## 17. 今後の次チャンク候補

### 候補 A: 未確定修正の採用/不採用フロー

完了報告時、フォーム由来の未確定修正を正本へ反映するか確認する仕組み。

```
未確定修正あり
  ↓ 採用 / 不採用
採用なら正本 JSON へ反映
  ↓
完了報告・アーカイブへ進む
```

### 候補 B: スマホ未表示問題の調査

保留中のスマホ表示を実機で潰す。見るべきもの:

- Console ログ
- JSONP 読み込み
- GitHub Pages キャッシュ
- Safari / Chrome 差

### 候補 C: 旧フォーム・旧回答シートの整理

古いフォームやスプレッドシートを残すか、アーカイブ扱いにするか決める。

### 候補 D: Google フォームの見た目改善

セクション分け・説明文・入力補助を整える。

---

## 18. 現時点の判断

**今回の作業は成功** と判断。

**重要な成果**

- 現場共有 **詳細修正フォーム V2** 作成。
- 枝切り・根切り **6 区分化**。
- V2 **entry ID** 取得・反映。
- 共有ページ **prefill V2 対応**。
- Apps Script **JSONP API V2** 対応。
- API レスポンスで **12 区分確認済み**。
- 旧項目 `branch_count` / `root_count` / `warning` / `edit_note` は **V2 API から除外**。

この段階で、現場共有ページの **詳細修正フォーム改善は一区切り**。

---

## 付録: 関連ファイル（再開時の入口）

| 種別 | パス |
|------|------|
| フォーム・prefill・ライブ編集 JS 生成 | `ippatsu-share-pages/scripts/generate_portal.py` |
| Apps Script ひな形（Part B） | `ippatsu-share-pages/docs/share_detail_edit_form_apps_script.md` |
| PC 側フィールド対応（別リポジトリ） | `ippatsu-pc/docs/share_detail_edit_form_field_map.md` |
| 共有モード設計（別リポジトリ） | `ippatsu-pc/docs/share_mode_design.md` |

---

*ログ作成: 作業記録として `docs/share_detail_edit_v2_work_log.md` に集約。このファイルのみ追加し、コード・data・JSON は変更しない。*
