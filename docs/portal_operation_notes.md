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
| **TOP 基準日** | 古い共有日を TOP から隠すときは `--mode portal-top-only --portal-min-date YYMMDD`（`share/` は削除しない。completed 自動連動なし）。**現行: `260611`**（2026-06-10。260610 完了 4 件反映後に更新）。 |
| **他ポータルを巻き込まない** | `portal/index.html` / `portal/archive/*` / `portal/negotiation/index.html` は **意図がない限り再生成しない**。 |
| **`git add .` 禁止** | 対象パスを明示して add（AGENTS.md §4）。 |
| **秘密情報** | API key / PIN / secrets の **実値をログ・チャット・commit に出さない**。 |
| **本番 data** | 会社PCの `ippatsu-pc-prod/data` 等で再生成確認。家PCでは本番 generate しない。 |
| **publish** | `main` への merge / push / GitHub Pages は **人間承認後**（AGENTS.md §4）。 |

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

## 関連ドキュメント

| パス | 内容 |
|------|------|
| `AGENTS.md` | repo 共通ルール・生成物ゾーン・git 制約 |
| `docs/work_logs/2026-05-29_1900_portal-regeneration-incident-summary.md` | 再生成事故と復旧の経緯 |
| `docs/work_logs/2026-05-29_2000_cursor_survey-visible-count-sync.md` | `dd436d0` の作業ログ（件数同期） |
| `docs/work_logs/2026-05-29_1930_cursor_survey-multipin-visible-sync.md` | `b130bce` の作業ログ（マルチピン同期） |

---

*最終更新: 2026-05-29 — 正本 `dd436d0`（main）*
