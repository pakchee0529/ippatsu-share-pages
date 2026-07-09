# portal 運用メモ（正本・再生成）

> **目的:** 現調待ちポータル（`portal/survey`）系の **基準点** と **正しい運用手順** を、後から迷わず参照するための運用ドキュメント。  
> **履歴・事故経緯** は `docs/work_logs/2026-05-29_1900_portal-regeneration-incident-summary.md` を参照。

---

## 1. 正本コミット（2026-05-29 時点）

| 項目 | 値 |
|------|-----|
| **branch** | `main` |
| **commit** | **`dd436d0`** — `Sync survey visible count with cards` |
| **前提** | `origin/main` と同期済みであること |

このコミットを **`portal/survey` 系の正本状態** として扱う。  
直前の関連コミット（参考）: `b130bce`（マルチピンと表示カード同期）、`372e92f`（focused CLI modes）、`7b10679`（2点地図・周辺電柱）、`01942b5`（survey UX 復旧）。

---

## 2. 正本とする範囲

`dd436d0` 時点で、以下が **生成元＋再生成結果として揃っている** ことを正本とする。

| 領域 | 内容 |
|------|------|
| 現調待ち表示 | `portal/survey/index.html` のカード一覧・overlay 連携 |
| 上部件数表示 | `#survey-visible-count` — **実際に表示されているカード数**（候補総数は `data-survey-candidate-total`） |
| 下部マルチピン | 表示中カードの座標のみ（`collectVisibleSurveyMultipinPoints`） |
| 2点地図 | `two-geo-*` JSON + 「2点地図を開く」 |
| 周辺160m電柱 | `nearby` ツールチップ（2点地図内） |
| survey UX | 現調済み／返却候補・overlay 警告・現場指示など |
| 返却候補 | 「返却候補にする」＋一覧からの非表示 |
| ハンバーガー | `portal-menu-btn` / サイトメニュー |
| focused CLI modes | `survey-only` / `archive-only` / `portal-top-only` / `negotiation-only` 等（`generate_portal.py`） |

**生成元（手修正しない）:**

- `scripts/generate_portal.py`
- `scripts/portal_immediate_status_client.py`

---

## 3. 正しい運用

| ルール | 説明 |
|--------|------|
| **HTML は手修正しない** | `portal/*.html` は生成物。差分は **スクリプト修正 → 限定再生成** のみ。 |
| **修正は生成元へ** | 表示・UX・件数・マルチピンは `generate_portal.py` と `portal_immediate_status_client.py` を編集する。 |
| **survey 更新は `survey-only`** | 現調待ちだけ更新するときは `--mode survey-only` を使う。 |
| **TOP 基準日** | 古い共有日を TOP から隠すときは `--mode portal-top-only --portal-min-date YYMMDD`（`share/` は削除しない。completed 自動連動なし・**archive 非連動**）。**現行: `260613`**（2026-06-12）。 |
| **他ポータルを巻き込まない** | `portal/index.html` / `portal/archive/*` / `portal/negotiation/index.html` は **意図がない限り再生成しない**。 |
| **完了報告 ≠ archive 反映** | ippatsu-pc で Supabase 完了報告しただけでは archive は更新されない。**§6 後続必須**。 |
| **`git add .` 禁止** | 対象パスを明示して add（AGENTS.md §4）。 |
| **秘密情報** | API key / PIN / secrets の **実値をログ・チャット・commit に出さない**。 |
| **本番 data** | 会社PCの `ippatsu-pc-prod/data` 等で再生成確認。家PCでは本番 generate しない。 |
| **publish** | `main` への merge / push / GitHub Pages は **人間承認後**（AGENTS.md §4）。 |

### 3.1 現調待ちGPS補完ルール（G9・仮想柱・引込）

現調待ちページの地図座標は `GPS.json` を正本として補完する。Supabase 側の行に `start_lat` / `start_lng` が入っていない場合でも、生成時点で `GPS.json` から解決できる座標はポータル表示に使う。

| ルール | 説明 |
|--------|------|
| **表示名は変えない** | 画面・検索・管理番号の元ラベルは交渉管理 / CS 受付の径間名を保持する。G9 等の補完は地図座標解決だけに使う。 |
| **G9 補完** | 山奥・危険な傾斜地の電柱は番号末尾に `G9` が付く。通常名で GPS が見つからない場合、裸番号は `95` → `95G9`、枝番は `95G1` → `95G1G9` の順に候補へ入れる。 |
| **K は仮想柱** | `K` は実在電柱ではない。GPS が存在しない場合は座標を作らない。反対側など解決できる実在柱があれば、その点を代表点にする。 |
| **片側欠損は代表点で表示** | 新設柱などで片側の GPS が未登録でも、もう片側が解決できる場合はその座標を代表点として `地図を開く` / `半径200m` に使う。 |
| **引込は実在柱側を使う** | `引込` は GPS キーではない。`中峰3W3～引込` のような径間は、実在柱側（例: `中峰3W3`）を代表点にする。 |
| **Supabase へは書き戻さない** | 明示承認がない限り、補完座標を Supabase に保存しない。生成HTML側の補完表示に留める。 |

代表例:

| 管理番号 | 元の径間名 | GPS解決ルール |
|----------|------------|---------------|
| `51406108` | `西川95～95G1` | `西川95G9～95G1G9` として解決 |
| `51406127` | `西川116G9～118G1G9` | `西川118G1G9` は未登録想定。`西川116G9` を代表点にする |
| `51406751` | `沼田原85K～86N1` | `K` は仮想柱。解決できる側を代表点にする |
| `51409718` | `出谷49G1～49G1S1` | `出谷49G1G9～49G1S1` として解決 |
| `51410306` | `中峰3W3～引込` | `中峰3W3` を代表点にする |

実装箇所: `scripts/generate_portal.py` の `_supplement_map_fields_from_gps`。詳細な作業ログは `docs/work_logs/2026-06-17_0000_survey-g9-virtual-pole-gps.md` を参照。

---

## 4. 代表コマンド（会社PC・現調待ちのみ再生成）

```powershell
cd C:\Users\kotan\Projects\ippatsu-share-pages
python scripts/generate_portal.py --mode survey-only --data-root C:\Users\kotan\Projects\ippatsu-pc-prod\data
```

終了時に **`validation: OK`** が出ること。NG の場合は生成物を commit しない。

---

## 5. 正本状態の確認項目

作業前・再生成後・publish 前に確認する。

### リポジトリ

- [ ] `git status` が **clean**（意図しない未追跡・生成物差分がない）
- [ ] `main` が **`origin/main` と同期**（`dd436d0` 以降を意図している場合）

### 生成物の意図しない差分がないこと

```powershell
git diff -- portal/index.html
git diff -- portal/archive/index.html
git diff -- portal/negotiation/index.html
```

いずれも **空** であること（survey-only のみ実行した場合）。

### `portal/survey/index.html`（ブラウザまたは HTML 確認）

- [ ] 上部リードの **表示件数** が、非表示カードを除いた **実表示件数** と一致（overlay 適用後も `updateSurveyVisibleCount` で追従）
- [ ] 下部 **マルチピン** が、表示中カードのピンのみ（件数・地図のズレなし）
- [ ] **2点地図** が開き、地図が表示される
- [ ] **「現調済みにする」** / **「返却候補にする」** ボタンがある
- [ ] **ハンバーガーメニュー**（`portal-menu-btn`）がある

### 代表データの残存（回帰用・任意）

- [ ] 管理番号 `51404162` / ラベル `白銀63N5W3～63N5W4` が一覧に含まれる（queue に載っている場合）

---

## 6. 完了報告後の completion archive 反映（必須後続）

> **背景（2026-06-12）:** 260605〜260612 の archive 未反映は、Supabase 完了報告後に export / manifest / `completion-archive` / publish が走らなかったため。backfill: [work_logs/2026-06-12_archive_backfill_260610_260611_260612.md](./work_logs/2026-06-12_archive_backfill_260610_260611_260612.md)

**正本:** Supabase `cases.status` + `completion_report_ref`。**副本:** ippatsu-pc `output/completion_reports_export/`（portal 生成直前に再 export。`data/completion_reports` は正本ではない・直接書かない）。

### 6.1 いつ必要か

ippatsu-pc で完了報告（GUI / `apply_completion_report_batch`）で Supabase を `completed` にした **直後**。portal TOP の `min-date` 更新や share 再生成とは **別タスク**。

### 6.2 手順（share-pages 側の責務は 4〜6）

1. **Supabase verify**（ippatsu-pc・read-only）— `completion_report_ref=YYMMDD` 件数、`completed` / `active=false` / `archive_state=stored`、同 `share_date_key` の未完了残存。
2. **export** — `python tools/export_completion_reports_from_supabase.py --dates YYMMDD --output-dir output/completion_reports_export`（ippatsu-pc）。`output/` は commit しない。
3. **未完了枠** — sdk に未完了が残る場合: **DB 変更禁止**（completed 化・ref 付与禁止）。export JSON の `planned_but_incomplete[]` に載せる（例: 260610 **51410041**、260612 **51405397**）。
4. **manifest** — `portal/archive_manifest.json` に entry merge。`item_count` / `completed_count` / `planned_incomplete_count` を export と整合。`href` はアーカイブ一覧基準の `./YYMMDD/` に統一し、削除対象の `../../share/YYMMDD/` は残さない。根拠なき手編集禁止。
5. **archive 限定再生成:**

```powershell
cd C:\Users\kotan\Projects\ippatsu-share-pages
python scripts/generate_portal.py --mode completion-archive --date YYMMDD `
  --completion-reports-root C:\Users\kotan\Projects\ippatsu-pc-prod\output\completion_reports_export
git restore portal/index.html   # completion-archive が TOP を触る副作用対策
```

6. **確認** — `portal/archive/index.html` と `portal/archive/YYMMDD/index.html`。`portal/index.html` と `share/**` に意図しない差分がないこと。公開前にアーカイブ表示の不変条件も検査する。

```powershell
python scripts/verify_archive_pages.py --date YYMMDD `
  --completion-reports-root C:\Users\kotan\Projects\ippatsu-pc-prod\output\completion_reports_export
```

7. **publish** — archive 関連と docs のみ明示 `git add` → commit → push（人間 Go 後）。

### 6.2.0 export / manifest の整合ルール

- `output/completion_reports_export/YYMMDD.json` は portal 公開素材の副本であり、commit しない。ただし生成直後に JSON として読めることを確認する。壊れた JSON のまま `completion-archive` 生成へ進めない。
- `portal/archive_manifest.json` の `href` は `portal/archive/index.html` から見たアーカイブ詳細 `./YYMMDD/` のみを許可する。
- 完了報告後の active share page は `share/YYMMDD/` から削除されるため、manifest から `../../share/YYMMDD/` を参照しない。
- `scripts/verify_archive_pages.py` は manifest の date / href、archive TOP の行、archive detail の存在・件数を公開前ガードとして検査する。

### 6.2.1 アーカイブTOPの件名ルール

`portal/archive/index.html` の各行に出す件名は、以下の優先順で生成する。

1. completion export `items[]` の `source_item.label`（完了/通常アーカイブ）
2. completion export `planned_but_incomplete[]` の `source_item.label`（当日予定・未完了枠）
3. 既存 `portal/archive/YYMMDD/index.html` のカードタイトル（古いアーカイブの補完）
4. 上記すべてが無い場合のみ `現場名未取得`

`—` のまま公開しない。古い日付で share ページや export JSON が無くても、詳細HTMLにカードが残っている場合はTOP件名へ補完する。検索文字列も同じ候補から組み立てる。

### 6.3 禁止

- 完了報告だけで archive 反映済みとみなす
- Supabase write と archive publish の混同
- `data/completion_reports` を正本扱い・直接書込
- `output/` の commit
- `--mode full`
- portal TOP 更新だけで archive 更新済みとみなす
- 未完了を archive に載せるための DB completed 化
- `git add .`

### 6.4 チェックテンプレ

```text
完了報告後 archive 反映チェック:

対象日: YYMMDD

1. Supabase verify
2. export_completion_reports_from_supabase.py --dates YYMMDD --output-dir output/completion_reports_export
3. share_date_key=YYMMDD の未完了案件を planned_but_incomplete として整理
4. archive_manifest merge
5. generate_portal.py --mode completion-archive --date YYMMDD --completion-reports-root <export root>
6. portal/archive 一覧・詳細を確認
7. portal TOP / share に差分がないことを確認
8. archive関連のみ commit/push
```

### 6.5 commit 対象（publish 時）

- `portal/archive/index.html`
- `portal/archive/YYMMDD/index.html`
- `portal/archive_manifest.json`
- `scripts/verify_archive_pages.py`（検証ロジックを更新した場合のみ）
- `docs/work_logs/*`（該当ログ）

**含めない:** `portal/index.html`、`share/**`、`output/`

---

## 関連ドキュメント

| パス | 内容 |
|------|------|
| `AGENTS.md` | repo 共通ルール・生成物ゾーン・git 制約 |
| `docs/work_logs/2026-05-29_1900_portal-regeneration-incident-summary.md` | 再生成事故と復旧の経緯 |
| `docs/work_logs/2026-05-29_2000_cursor_survey-visible-count-sync.md` | `dd436d0` の作業ログ（件数同期） |
| `docs/work_logs/2026-05-29_1930_cursor_survey-multipin-visible-sync.md` | `b130bce` の作業ログ（マルチピン同期） |
| `docs/work_logs/2026-06-12_archive_backfill_260610_260611_260612.md` | archive 未反映 backfill と planned 未完了枠 |
| ippatsu-pc `docs/next_cursor_tasks.md` §完了報告後 archive 反映 | export・verify・禁止ルール |

---

*最終更新: 2026-06-12 — §6 完了報告後 archive 後続必須を追加*
