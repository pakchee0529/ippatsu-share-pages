# portal TOP 基準日更新 — min_date=260612（2026-06-11）

## 背景

260611 の6件が完了報告済み（Supabase `completed`）のため、portal TOP から 260611 を非表示にし、次の予定 260612 を先頭表示にする。

## コマンド

```powershell
python scripts/generate_portal.py --mode portal-top-only --portal-min-date 260612
```

## 結果

| 項目 | 値 |
|------|-----|
| portal_min_date | **260612** |
| TOP カード数 | **1**（260612 のみ） |
| 260612 件数表示 | **4件** |
| validation | OK |

## 確認

| 項目 | 結果 |
|------|------|
| TOP に 260611 なし | OK |
| TOP に 260612 あり | OK |
| `share/260611/index.html` 残存 | OK（削除なし） |
| `portal/archive/` | 未変更 |
| Supabase / share 再生成 | **なし** |

## 参照

ippatsu-pc: [`2026-06-11_completion_report_gui_260611_6cases.md`](https://github.com/pakchee0529/ippatsu-pc/blob/worktree/prod-daily/docs/work_logs/2026-06-11_completion_report_gui_260611_6cases.md)
