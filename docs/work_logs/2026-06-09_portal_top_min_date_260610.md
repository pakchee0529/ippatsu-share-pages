# portal TOP 基準日フィルタ — min_date=260610（2026-06-09）

## 背景

ippatsu-pc 側で share_date_key <= 260609 の完了報告 backlog を Supabase `completed` 反映済みだが、
portal TOP は **share フォルダ走査 + archive manifest 除外**のみで、completed status と連動していなかった。

## 現状仕様（変更前）

| 項目 | 内容 |
|------|------|
| TOP 一覧の元 | `share/<YYMMDD>/index.html` の存在（share-pages リポジトリ走査） |
| 除外 | `RETIRED_SHARE_DATE_KEYS`（261231）、`portal/archive_manifest.json` に載る日付 |
| completed 参照 | **なし**（Supabase / cases.status は見ない） |
| 日付フィルタ | **なし**（manifest 除外のみ） |

## 実装仕様（変更後）

| 項目 | 内容 |
|------|------|
| CLI | `--portal-min-date YYMMDD`（別名 `--hide-before-date`） |
| 効果 | TOP カードは **当該日付以上**のみ（`folder >= min_date`）。未満は非表示 |
| 非触領域 | `share/<date>/` 削除なし、Supabase なし、archive なし、manifest なし |

```powershell
python scripts/generate_portal.py --mode portal-top-only --portal-min-date 260610
```

## 今回の生成結果

| 項目 | 値 |
|------|-----|
| 基準日 | **260610** |
| TOP カード数 | **3**（260610 / 260611 / 260612） |
| TOP から消えた例 | 260604, 260605, 260606, 260608, 260609 |
| share ページ | 上記日付含め **すべて disk 上に残存** |
| validation | OK |

## 確認

- portal TOP に 260604–260609 **なし**
- portal TOP に 260610 以降 **あり**
- `share/260604/index.html` 等 **削除なし**
- archive / manifest **未変更**
- Supabase write **なし**

## 残タスク

- 基準日の運用ルール（誰がいつ `--portal-min-date` を更新するか）を ippatsu-pc 運用メモと整合
- 将来: `today` 自動化は **別設計**（今回は明示日付のみ）
