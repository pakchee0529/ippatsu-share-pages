# completion archive 限定公開 — 結果ログ

日付: 2026-06-03  
リポジトリ: ippatsu-share-pages  
**人間 Go 済み — archive HTML のみ commit/push**

---

## A. 結論

Supabase export 由来の完了報告アーカイブ（260518/519/520/529）を **portal/archive 関連 HTML のみ** 公開した。share ページは今回の commit に含めていない。

| 日付 | 件数 |
| ---- | ---- |
| 260518 | 4 |
| 260519 | 6 |
| 260520 | 7 |
| 260529 | 1（incomplete 3 件は含めない） |

---

## B. export 再生成結果

ippatsu-pc（read-only）:

```text
python tools/export_completion_reports_from_supabase.py \
  --dates 260518 260519 260520 260529 \
  --output-dir output/completion_reports_export \
  --compare-legacy
```

- 件数: 4 / 6 / 7 / 1
- `portal_field_gaps_in_export`: 空
- Supabase write なし / `data/completion_reports` 未変更

---

## C. full 生成結果

```text
python scripts/generate_portal.py --mode full \
  --completion-reports-root <ippatsu-pc>/output/completion_reports_export \
  --strict-completion-reports-root \
  --strict-completion-reports-summary
```

- exit 0
- `source=explicit`
- strict-summary 不一致なし

---

## D. 公開対象ファイル（commit に含めた）

- `portal/archive/260518/index.html`
- `portal/archive/260519/index.html`
- `portal/archive/260520/index.html`
- `portal/archive/260529/index.html`
- `portal/archive/index.html`
- `portal/archive_manifest.json`（差分なし・整合確認のため add）
- `docs/work_logs/2026-06-03_completion_archive_publish_result.md`
- `docs/next_cursor_tasks.md`

**含めなかった:** 他 `portal/archive/<date>/`、`portal/negotiation/`、`share/**`、`output/`

---

## E. share 差分を含めなかった理由

- 今回の公開スコープは **完了報告アーカイブのみ**
- `full` 実行で share に detail-edit inject 差分が出るが、archive 公開と無関係
- 別タスクで share 公開を判断する

---

## F. 260529 incomplete 3 件

- 51404109 / 51404117 / 51404127: archive HTML に **なし**
- 51404222: **あり**（完了 1 件）
- manifest: `item_count=1`, `completed_count=1`, `incomplete_count=0`

---

## G. commit hash

（push 後に `git log -1` で記録）

---

## H. push 結果

`git push origin main`（push 後に記録）

---

## I. git status

push 後: archive 5 ファイルは clean。`share/**` 等はローカル M のまま残る想定。

---

## J. GitHub Pages 反映確認

push 後に `portal/archive/260529/` 等を HTTP GET（反映遅延 1–5 分の可能性あり）。

---

## K. 人間確認事項

1. 本番 URL で 260529 が 1 カードのみか
2. 260518/519/520 の代表現場
3. share 差分を別途公開するか

---

## L. 次にやるべきこと

1. Pages 反映の目視
2. 任意: 公開成功後 ippatsu-pc `data/completion_reports` snapshot
3. `export_summary.exported_at` 鮮度チェック（残タスク）
4. share / negotiation 差分の別公開判断
