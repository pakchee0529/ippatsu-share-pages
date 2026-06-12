# portal TOP 基準日更新 — min_date=260613（2026-06-12）

## 背景

260612 は5件完了・51405397のみ未完了で**終了扱い**。portal TOP から 260612 を非表示にし、次の日付以降を TOP 対象とする。

| 状態 | 内容 |
|------|------|
| 260612 completed | 51405219/215/213/211/207（5件） |
| 260612 未完了 | 51405397（construction_wait 維持・TOP入口不要） |
| share/260612 | **残存**（直接URL利用可） |

## コマンド

```powershell
python scripts/generate_portal.py --mode portal-top-only --portal-min-date 260613
```

## 結果

| 項目 | 値 |
|------|-----|
| portal_min_date | **260613** |
| TOP カード数 | **0**（260613 以降の share 日付未公開） |
| 260612 TOP 表示 | **なし** |
| validation | OK |

## 確認

| 項目 | 結果 |
|------|------|
| TOP に 260612 なし | OK |
| `share/260612/index.html` 残存 | OK |
| `portal/archive/` | 未変更 |
| Supabase write | **なし** |

## 参照

ippatsu-pc: [`2026-06-12_completion_report_260612_5cases_leave_51405397.md`](https://github.com/pakchee0529/ippatsu-pc/blob/worktree/prod-daily/docs/work_logs/2026-06-12_completion_report_260612_5cases_leave_51405397.md)
