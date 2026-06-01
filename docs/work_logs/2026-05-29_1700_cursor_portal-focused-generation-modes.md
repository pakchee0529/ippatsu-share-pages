# 作業ログ: portal 限定再生成 CLI モード (P1–P3)

| 項目 | 値 |
|------|----|
| 日時 | 2026-05-29 17:00 |
| 担当 | cursor |
| repo | ippatsu-share-pages |
| branch | main（未 commit） |

## 変更ファイル

- `scripts/generate_portal.py`
- `scripts/portal_immediate_status_client.py`（交渉待ち返却候補 overlay JS をサーバー取得に同期）
- `portal/survey/index.html`（survey-only テスト再生成）
- `portal/archive/index.html`（archive-only テスト再生成）
- `portal/index.html`（portal-top-only テスト再生成）
- `portal/negotiation/index.html`（negotiation-only テスト再生成）

## 実施内容

- `--mode survey-only` / `archive-only` / `portal-top-only` / `negotiation-only` 追加
- `--data-root` + `load_portal_dotenv`（share-pages / ippatsu-pc `.env`）
- 各 mode の portal HTML 変更ガード（4 主要 HTML のスナップショット比較）
- mode 別 HTML スモーク検証（7 件・two-geo・ハンバーガー・today-schedule 等）
- `build_negotiation_html` を survey と同様のハンバーガー + 返却待ちセクション + two-geo JSON 修正に同期

## 守った制約

- `git add .` なし、push なし
- prod queue / Supabase / data/share 未変更
- secret 実値ログなし

## 次に必要な作業

- 人間確認後 commit（生成物は各 mode 単体運用を確認してから add）
