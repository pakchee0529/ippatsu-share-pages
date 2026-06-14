# 作業ログ: 案件管理ページ視認性改善

| 項目 | 値 |
|------|----|
| 日時 | 2026-06-14 18:47 |
| 担当 | cursor |
| repo | ippatsu-share-pages |
| branch | main |

## 変更ファイル

- `scripts/generate_portal.py`
- `portal/cases/index.html`

## 実施内容

- 案件管理ページに検索ボックスを追加した。
- 管理番号・径間名・状態で絞り込みできるようにした。
- 絞り込み時に合計件数と各ステータス見出しの件数が更新されるようにした。
- ステータス別の色分け、状態バッジ、管理番号の強調表示を追加した。
- カード余白、影、背景、モバイル表示を調整した。

## 守った制約

- 閲覧専用ページのままにし、DB write や更新操作は追加していない。
- 個人情報は表示していない。
- publish / deploy / push は実施していない。
- `git add .` は使用していない。

## 確認

- `python -m py_compile scripts\generate_portal.py`
- `python scripts\generate_portal.py --mode cases-only`
- ローカルHTTP経由のブラウザ確認で、検索前77件、`515 10213`検索後1件への絞り込みを確認。
