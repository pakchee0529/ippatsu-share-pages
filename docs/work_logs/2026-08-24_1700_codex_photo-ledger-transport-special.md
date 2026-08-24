# 作業ログ: 写真台帳の運搬・特殊入力分離

| 項目 | 値 |
|------|----|
| 日時 | 2026-08-24 17:00 |
| 担当 | codex |
| repo | ippatsu-share-pages |
| branch | cursor/photo-ledger-transport-special-input |

## 変更ファイル

- `portal/ledger-input/index.html`

## 実施内容

- 運搬を車種（軽四輪／2t車）選択と指定場所運搬チェックに変更した。
- 倒木実費と自由記述を別項目に分離した。
- 自由記述は区分テキスト欄と写真番号欄を別にした。
- 既存のJSON `transport` / `special` 形式を維持した。

## 守った制約

- Supabase、写真原本、共有ページ生成器、実データは変更していない。

## 確認

- HTML構造・必須項目・差分検査を実施した。
