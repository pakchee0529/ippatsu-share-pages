# AGENTS.md — ippatsu-share-pages エージェント共通ルールブック

> **このファイルを最初に読む。** 作業開始前に本ファイルと **ippatsu-pc** 側 `AGENTS.md` の禁止事項を確認する。
> 母艦リポジトリの運用ルールは `ippatsu-pc/AGENTS.md` を正とする。本ファイルは **この repo 固有**のルールを補う。

---

## 0. このリポジトリの位置づけ

| 項目 | 内容 |
|------|------|
| **役割** | GitHub Pages 公開用の **静的共有ページ** repo |
| **母艦** | **ippatsu-pc**（GUI・CLI・Supabase・業務 data の正本） |
| **業務 data** | `ippatsu-pc-prod/data` 等、**ippatsu-pc 側**が正本。この repo 単体で業務状態を判断しない |
| **公開 URL** | `https://pakchee0529.github.io/ippatsu-share-pages/` |
| **主要生成物** | `portal/`（入口・現調・交渉・アーカイブ）、`share/<date>/`（日別共有ページ） |

**作業開始前（必須）:**

```
git status -sb
git log --oneline --decorate -5
```

- `git status` が **clean** でない場合は、勝手に stash / restore / add せず人間に報告して停止する。
- 業務フロー（完了報告・ポータル再生成・publish）の詳細は ippatsu-pc の `docs/worktree_prod_operations.md` を参照。

### 0.1 家PC / 会社PC

| 項目 | 家PC（`C:\Users\yawar\`） | 会社PC（`C:\Users\kotan\`） |
|---|---|---|
| 本番 `data/survey/queue.json` | **なし** | `ippatsu-pc-prod/data` に存在 |
| Supabase `.env` | **なし** | ippatsu-pc 側に配置 |
| **本番 generate 確認** | ❌ しない | ✅ 会社PC・本番 data で行う |
| **GitHub Pages publish** | ❌ 人間承認必要 | ✅ 人間が実施 |
| AGENTS.md / docs 編集 | ✅ 可 | ✅ 可 |

---

## 1. 役割分担

| エージェント | 主な担当 | 備考 |
|---|---|---|
| **ChatGPT** | 設計・任務書・停止条件・危険判定・レビュー観点 | 長期状態の正本は AGENTS.md / docs / ippatsu-pc 側 work_logs |
| **Cursor Agents Window** | 実装・調査・検証・branch / commit・diff 整理 | **push / publish / main merge は人間承認後のみ** |
| **Cursor Editor / Chat** | 小規模確認・diff レビュー・手動微修正・質問応答 | 大きな実装や commit は原則 Agents Window へ |
| **Claude Cowork** | AGENTS.md・docs・開発ハーネス整理 | コード実装・publish / push はしない |
| **人間（りょーまさん）** | publish・push・本番 data 検証・secret 判断・最終承認 | 不可逆操作は必ず人間が実施 |

---

## 2. ファイルゾーン

### 🟢 自由に読み書きしてよい

- `AGENTS.md`（本ファイル）
- `docs/*` — 設計メモ・作業ログ（既存ログの大幅改変は禁止）

### 🟡 変更は設計確認後・ブランチで・差分を小さく

- **`scripts/generate_portal.py`** — ポータル全体の生成スクリプト。**安易に触らない。** 変更が必要な場合は ChatGPT / Cowork で設計確認 → Cursor Agents Window で `cursor/*` ブランチ実装 → 人間確認。

### 🔴 基本は生成物 — 手編集禁止

| パス | 扱い |
|------|------|
| `portal/index.html` | `generate_portal.py` で再生成 |
| `portal/survey/index.html` | 現調待ちポータル（生成物） |
| `portal/negotiation/index.html` | 交渉待ちポータル（M11 等で追加。main 未 merge 時はブランチ上のみ） |
| `portal/archive/*` | 完了報告アーカイブ（生成物） |
| `share/<date>/index.html` | 日別共有ページ（ippatsu-pc からコピー or 生成） |

生成物を直編集しない。**目的ファイルだけ**明示 `git add` する（`git add .` 禁止）。

### 🔴 絶対に commit しない

- `.env` / `.env.*` / 一時 env ファイル
- secret / token / service_role / Access Token の **実値**
- 意図しない広範囲の `portal/*`・`share/*` 差分

---

## 3. `generate_portal.py` の扱い

| 出力 | 意味 |
|------|------|
| `portal/survey/index.html` | 現調待ちポータル（`data/survey/queue.json` 起点） |
| `portal/negotiation/index.html` | 交渉待ちポータル（M11。ブランチ上のみの場合あり） |
| `portal/index.html` | ポータル入口 |
| `portal/archive/*` | 完了報告アーカイブ |

**モード（ippatsu-pc から呼ばれる場合）:** `--mode full` / `share-update` / `completion-archive` 等。詳細は ippatsu-pc `docs/worktree_prod_operations.md`。

**ルール:**

- **`full` generate** は `portal/survey`・他日付 `share/*` など **広範囲の差分**を出し得る。目的外の生成物を stage しない。
- 生成確認は **会社PCの本番 data**（`--data-root` で `ippatsu-pc-prod/data` 等）で行う。
- **家PCでは本番 generate を実行しない**（本番 data / `.env` なし）。
- スクリプト変更と生成物 commit は **分離**し、生成 diff は許可パスのみ add する。

---

## 4. Git / publish ルール

- **`git add .` 禁止** — 対象パスを明示して add
- **`force push` 禁止**
- **`main` への直接 push 禁止** — 人間承認後のみ（通常は `cursor/*` → PR / merge）
- **GitHub Pages publish**（`main` への merge + push）は **人間承認必須**
- 作業は **`cursor/*` ブランチ**で行う
- PC 間同期は ippatsu-pc `docs/git_sync_workflow.md` に従う

### M11 ブランチ（交渉待ちポータル）

| 項目 | 内容 |
|------|------|
| ブランチ | `cursor/m11-portal-negotiation-page` |
| 状態 | 実装済み・origin push 済み。**main 未 merge・publish 未実施** |
| ルール | **勝手に `main` へ merge しない**。会社PC 本番 data 検証・人間 Go 後のみ |

---

## 5. Secret / API key ルール

以下の **実値**を表示・commit・公開 HTML へ直書き **禁止**:

- `SUPABASE_SERVICE_ROLE_KEY`
- `SUPABASE_ANON_KEY`
- `PORTAL_SURVEY_REQUEST_API_KEY`
- `SUPABASE_ACCESS_TOKEN`
- その他 secret / token / publishable key の実値

**追加ルール:**

- **`service_role` は絶対に公開 HTML に出さない**
- 公開 HTML に載せてよいのは、設計上 **公開前提と明示された** publishable / anon 相当のみ（例: Edge Function 呼び出し用 apikey ヘッダ）。**それでも値の表示やチャットへの貼り付けは避ける**
- 生成スクリプトが HTML に埋め込む定数は、レビューで secret でないことを確認してから commit

---

## 6. Edge Function / survey request 関連

- ポータル（ブラウザ）から **`cases` を直接 UPDATE しない**
- 「現調済みにする」報告は **Edge Function 経由**で `survey_status_update_requests` へ **request INSERT のみ**
- **apply / reject**（本体 data 反映）は **ippatsu-pc 側**で人間承認後（`tools/dry_run_apply_survey_update_request.py`）
- **Edge Function deploy / CORS / verify_jwt / Secret 変更**は **ippatsu-pc** の `supabase/functions/*` で行う。この repo から実行しない

---

## 7. 完了報告

作業完了時は次を必ず報告する。

```markdown
## 変更ファイル
## 実装内容
## 実行した確認
## 生成物を触ったか
## publish / push していないこと
## 次に人間が確認すべきこと
```

---

## 参照（ippatsu-pc 側）

- `AGENTS.md` — 母艦の共通ルール・家PC/会社PC 制約
- `docs/worktree_prod_operations.md` — 業務 worktree・P1a 許可リスト・generate モード
- `docs/git_sync_workflow.md` — 家PC / 会社PC 同期
- `docs/survey_portal_update_request_mvp_design.md` — 現調更新依頼 MVP
