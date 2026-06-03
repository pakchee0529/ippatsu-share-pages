# planned_but_incomplete status UI 公開結果

日付: 2026-06-03  
前提コード: `17a63b1dbefef4c40695628ca1b02e325eeada2f`

制約: Supabase write なし / `data/` 未変更 / `share/**` 未 commit

---

## 公開内容

- `portal/archive/260529/index.html` — 第2枠から内部 status 行を除去、説明文更新
- `portal/archive/index.html` — 260529 行 `完了 1件 / 当日未完了 3件`（前回公開と同一の場合あり）

## ローカル確認

| 項目 | 結果 |
| ---- | ---- |
| 完了 | 51404222 |
| 第2枠 | 51404109 / 51404117 / 51404127 |
| 英語 status / active / ref | HTML になし |
| 注意文 | セクション冒頭 1 回 |
| 一覧 260529 | `完了 1件 / 当日未完了 3件` |

## 生成

```text
ippatsu-pc: export 260529 --attach-legacy-incomplete
share-pages: generate_portal.py --mode full --completion-reports-root .../completion_reports_export_incomplete
```

## 本番 URL

- https://pakchee0529.github.io/ippatsu-share-pages/portal/archive/
- https://pakchee0529.github.io/ippatsu-share-pages/portal/archive/260529/

Pages 反映に数分かかる場合あり。
