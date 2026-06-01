# portal 再生成事故と復旧まとめ

| 項目 | 値 |
|------|----|
| 日時 | 2026-05-29 |
| 担当 | cursor / 人間（りょーまさん） |
| repo | ippatsu-share-pages |
| 目的 | 再生成事故の経緯・復旧・再発防止を後から読める形で整理 |

---

## 1. 概要

### 何が起きたか

現調待ち 7 件追加のあと、`portal/survey/index.html` 等を **再生成**した際、**生成物にだけ入っていた UX 改善**（現調済み／返却候補 overlay、ハンバーガーメニュー、2 点地図の JSON 埋め込みなど）が **古いテンプレートで上書き**され、公開ページが一時的に壊れた。

### どのページに影響したか

| ページ | 主な症状 |
|--------|----------|
| `portal/survey/index.html` | UX ロールバック、ハンバーガー消失、2 点地図が空枠 |
| `portal/archive/index.html` | ハンバーガーメニュー消失 |
| `portal/negotiation/index.html` | （再生成すると）メニュー・返却待ちが generator 未反映で戻るリスク（372e92f で generator 同期） |
| `portal/index.html` | full / portal-top-only 実行時は TOP 全体が書き換わる（今回の commit 372e92f では **含めず**） |

### 最終的にどう直したか

1. **01942b5** — survey UX・survey/archive ハンバーガーを **生成元**（`generate_portal.py` / `portal_immediate_status_client.py`）に戻し、HTML を再生成。
2. **7b10679** — 2 点地図の `two-geo` JSON 埋め込みバグ修正 + 周辺 160m 電柱（`nearby`）表示。
3. **372e92f** — **限定 CLI モード**（`survey-only` 等）+ 変更ガード + mode 別自動検証。今後は `python -c` 直呼びや不用意な `full` を避ける。

**結論:** 正本は **`portal/*.html` ではなく** `scripts/generate_portal.py` と `scripts/portal_immediate_status_client.py`。再生成は **正式 `--mode` のみ**、対象 HTML だけ。

---

## 2. 発端

### 現調待ち 7 件追加

本番 `ippatsu-pc-prod/data/survey/queue.json` に 7 件を追加し、Supabase `cases` にも INSERT。共有ポータルへ反映するため **`portal/survey/index.html` の再生成**が必要になった。

追加 7 件（管理番号 / ラベル）:

| 管理番号 | ラベル |
|----------|--------|
| 514 04162 | 白銀63N5W3～63N5W4 |
| 514 02038 | 上之4W4～4W5 |
| 514 10139 | 江出2N14～生子93E1 |
| 514 10418 | 向山7S1～7S2 |
| 514 10417 | 城戸11W1～大日川2 |
| 514 00394 | 芦ヶ瀬1～2 |
| 514 03794 | 鹿場16W7～16W8 |

### queue / Supabase / portal HTML の二層構造

| 層 | 正本の場所 | 役割 |
|----|------------|------|
| 業務 data | `ippatsu-pc-prod/data/survey/queue.json` 等 | 現調待ち・交渉待ちの **案件一覧の正本** |
| Supabase | `cases` 等 | PC／クラウド連携・overlay 用 |
| 公開 HTML | `portal/survey/index.html` 等 | GitHub Pages 向け **静的生成物**（`generate_portal.py` 出力） |

**portal HTML だけ直しても** queue / Supabase とズレる。**queue 更新 → 限定再生成** が正しい流れ。

### portal/survey 再生成が必要になった理由

7 件は queue に載ったが、GitHub Pages の現調待ち一覧は **生成 HTML** なので、`load_survey_public_items` + `build_survey_html` による **survey 再生成**が必要だった。

---

## 3. 事故内容

### 3.1 survey UX ロールバック

再生成後、以下が **古い状態に戻った**（または欠落）:

- 「**現調済みにする**」（即時 status overlay）
- 「**返却候補にする**」
- **overlay 連携**（`fetchReturnCandidates` / `applySurveyOverlay` 3 引数版）
- **`survey-overlay-warning`**
- **API key 注入**（`PORTAL_STATUS_API_KEY` — publishable/anon のみ。実値はログ禁止）
- `portal_immediate_status_client.py` 由来の **B-plan 即時反映 JS**

**見え方:** ボタンが無い／無効、返却候補の警告が出ない、overlay が効かない。

### 3.2 survey/archive ハンバーガーメニュー消失

- `portal/survey/index.html` — `portal-menu-btn` / サイトメニュー導線が消えた
- `portal/archive/index.html` — 同様

**原因:** ハンバーガーは **HTML 手修正や一時的な生成**で入っていたが、`build_survey_html` / `build_archive_html` のテンプレートに **恒久反映されていなかった**。

### 3.3 2点地図 JSON.parse 失敗

- `two-geo-*` を `escape_html(json.dumps(...))` で埋め込んでいた
- HTML 内が `{&quot;a&quot;:...}` となり、クリック時の **`JSON.parse(jsonEl.textContent)` が失敗**
- **Leaflet・ボタン・下部多点地図**は動作（地図枠だけ開いて中身が空に見える）

**分類:** 生成バグ（C）。UTF-8 BOM は副次要因（`applySurveyOverlay` 前）だが、主因は JSON の過剰エスケープ。

---

## 4. 根本原因

1. **`portal/*.html` 手修正と生成元の乖離**  
   見た目は直っても、再生成で **テンプレートが勝つ**。

2. **`generate_portal.py` の再生成範囲が広い**  
   `--mode full` や ad hoc `python -c` で **survey 以外も巻き込む**運用だった。

3. **survey-only 等の正式 CLI がなかった**  
   「survey だけ更新したい」が **内部関数直呼び**や full に流れ、事故りやすかった。

4. **`two-geo` JSON の HTML escape バグ**  
   `application/json` スクリプトタグなのに `escape_html` しており、仕様上パース不能。

5. **（運用）queue / Supabase / HTML の片方だけ更新**  
   data は増えたが generator が古い UX のまま、という **二重のズレ**。

---

## 5. 実施した修正

### 01942b5 — Restore survey portal generator UI

| 対象 | 内容 |
|------|------|
| `scripts/generate_portal.py` | survey / archive のハンバーガー、survey 即時 status・返却候補 UI をテンプレートに復元 |
| `scripts/portal_immediate_status_client.py` | `applySurveyOverlay` 3 引数版など survey 用 JS |
| `portal/survey/index.html` | 再生成 |
| `portal/archive/index.html` | 再生成（メニュー復旧） |

**直したこと:** 事故 1・2（UX ロールバック、ハンバーガー消失）。

### 7b10679 — Fix survey two-point map with nearby poles

| 対象 | 内容 |
|------|------|
| `scripts/generate_portal.py` | `json_for_script_tag` / `format_two_geo_script`（`&quot;` 回避、`<` → `\u003c`） |
| | `nearby` — 始点・終点・**中点**のいずれかから **160m**、端点 ±3m 除外、GPS.json 全点から haversine |
| | 端点 `two-tip-endpoint` / 周辺 `two-tip-nearby`、`fitBounds` padding |
| `portal/survey/index.html` | survey のみ再生成（prod data + `.env`） |
| `scripts/portal_immediate_status_client.py` | BOM 除去（副次） |

**直したこと:** 事故 3（2 点地図）。7 件追加データは維持（`visible 39` 等）。

### 372e92f — Add focused portal generation modes

| 対象 | 内容 |
|------|------|
| `scripts/generate_portal.py` | `--mode survey-only` / `archive-only` / `portal-top-only` / `negotiation-only` |
| | `load_portal_dotenv`、`apikey_nonempty` bool 出力 |
| | **許可外 portal HTML 変更ガード**、mode 別 **自動検証**（失敗時 exit 1） |
| | `build_negotiation_html` を survey 同様のメニュー・返却待ち・two-geo 修正に同期 |
| `scripts/portal_immediate_status_client.py` | 交渉ページの `fetchReturnCandidates` をサーバー取得版に同期 |
| `portal/survey/index.html` | survey-only テスト再生成分 |
| `portal/negotiation/index.html` | negotiation-only テスト再生成分 |
| **含めず** | `portal/index.html` / `portal/archive/index.html`（CRLF のみの差分のため） |

**直したこと:** 再発防止基盤。今後は mode 単位で安全に再生成可能。

### 参考: a4e42e6（事故発生点の一つ）

- `Update survey portal with new survey wait cases` — 7 件追加に伴う survey 再生成のコミットの一つ。
- この前後で **generator と HTML の乖離**が表面化し、以降 01942b5 / 7b10679 / 372e92f で段階復旧。

---

## 6. 現在の正しい運用

**必ず:** 会社 PC・本番 data・`.env`（`ippatsu-pc/.env`）を読み、`apikey_nonempty: true` を確認（実値は出さない）。

### survey

```powershell
cd C:\Users\kotan\Projects\ippatsu-share-pages
python scripts/generate_portal.py --mode survey-only --data-root C:\Users\kotan\Projects\ippatsu-pc-prod\data
```

**触るファイル:** `portal/survey/index.html` のみ（ガード + 検証付き）。

### archive

```powershell
python scripts/generate_portal.py --mode archive-only --data-root C:\Users\kotan\Projects\ippatsu-pc-prod\data
```

**触るファイル:** `portal/archive/index.html` のみ。

### TOP

```powershell
python scripts/generate_portal.py --mode portal-top-only --data-root C:\Users\kotan\Projects\ippatsu-pc-prod\data
```

**触るファイル:** `portal/index.html` のみ（`today-schedule` 等を検証）。

### negotiation

```powershell
python scripts/generate_portal.py --mode negotiation-only --data-root C:\Users\kotan\Projects\ippatsu-pc-prod\data
```

**触るファイル:** `portal/negotiation/index.html` のみ。

### 使わない／慎重に

| 操作 | 注意 |
|------|------|
| `--mode full` | survey / archive / negotiation / share inject 等 **広範囲** — 目的外差分を出しやすい |
| `python -c` で `build_survey_html` 直呼び | 正式 CLI なし — **372e92f 以降は禁止** |
| `portal/*.html` 手編集 | 再生成で消える — **正本にしない** |

---

## 7. 再発防止ルール

1. **`portal/*.html` を直接直して終わらせない** — 必ず generator / client JS を直す。
2. **`generate_portal.py` / `portal_immediate_status_client.py` を正本**にする。
3. **`full` generate を不用意に使わない** — 必要な `--mode` だけ。
4. **mode 別 CLI を使う** — 上記 §6。
5. **`git add .` 禁止** — 対象パスを明示。
6. **commit 前に** `portal/index.html` / `archive` / `survey` / `negotiation` の差分を確認（意図外なら止める）。
7. **API key 実値はログ・チャットに出さない** — `apikey_nonempty` のみ。
8. **queue / Supabase 二層更新** — 片方だけで終わらせない（業務 data と公開 HTML の両方を意識）。
9. **生成物 commit** — スクリプト変更と分離し、許可パスのみ `git add`。

---

## 8. 検証チェックリスト

### survey（`survey-only` 後 + 目視）

- [ ] 7 件が残っている（例: `51404162` / `白銀63N5W3～63N5W4`、`51403794`）
- [ ] 「現調済みにする」
- [ ] 「返却候補にする」
- [ ] `survey-overlay-warning`
- [ ] `fetchReturnCandidates`
- [ ] 「2点地図を開く」— marker・線・**nearby** 周辺電柱
- [ ] `two-geo-0` に `&quot;` がない / `JSON.parse` 成功
- [ ] 下部多点地図（`var points`）
- [ ] ハンバーガーメニュー（`portal-menu-btn`）

### archive（`archive-only` 後）

- [ ] ハンバーガーメニュー
- [ ] TOP / 現調待ち / 交渉待ち / 社内カレンダー導線

### TOP（`portal-top-only` 後 — 必要時のみ）

- [ ] `today-schedule`
- [ ] `loadTodaySchedule`
- [ ] `company-calendar-events`
- [ ] `./calendar/` 導線

### negotiation（`negotiation-only` 後 — 必要時のみ）

- [ ] 返却待ち（`return-candidate-section`）
- [ ] 交渉待ちカード・「現調待ちに戻す」
- [ ] ハンバーガーメニュー
- [ ] `fetchReturnCandidates`

**CLI 自動検証:** 各 mode 終了時に `validation: OK` が出ること（NG なら exit 1 で止まる）。

---

## 9. 残課題

- **queue / Supabase 二層構造の整理** — 正本・更新手順の一本化（ippatsu-pc 側ドキュメントと合わせる）。
- **`share-update` / `full` generate の責務整理** — いつ full が必要か、P1a 許可リストとの関係。
- **共有ページ再設計モックの本格反映** — generator への取り込み計画。
- **作業ログ / 設計ログの粒度** — 1 作業 1 ファイル（`docs/work_logs/`）の継続。

---

## 10. 関連コミット

| hash | message | 役割 |
|------|---------|------|
| **a4e42e6** | Update survey portal with new survey wait cases | 7 件追加に伴う survey 更新（事故の引き金の一つ） |
| **01942b5** | Restore survey portal generator UI | survey UX + survey/archive ハンバーガー復旧 |
| **7b10679** | Fix survey two-point map with nearby poles | two-geo JSON + nearby 160m |
| **372e92f** | Add focused portal generation modes | 限定 CLI・ガード・検証・negotiation generator 同期 |

### 関連作業ログ（詳細）

- `docs/work_logs/2026-05-29_1800_cursor_survey-portal-generator-restore.md`（01942b5 付近）
- `docs/work_logs/2026-05-29_1637_cursor_survey-two-point-map-nearby-poles.md`（7b10679 付近）
- `docs/work_logs/2026-05-29_1700_cursor_portal-focused-generation-modes.md`（372e92f 付近）

---

## 再開時の最短手順

1. `git log --oneline -5` で **372e92f 以降**か確認。
2. 現調待ちだけ更新 → **`survey-only`** + §8 survey チェック。
3. UX 変更 → **generator / client を先に編集** → 該当 mode で再生成 → 検証 OK を確認してから commit。
4. **push / GitHub Pages** は人間承認後（AGENTS.md §4）。
