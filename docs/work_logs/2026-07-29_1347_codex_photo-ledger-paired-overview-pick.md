# 作業ログ: 写真台帳の伐採前後一括採用・表示順修正

| 項目 | 値 |
|------|----|
| 日時 | 2026-07-29 13:47 |
| 担当 | codex |
| repo | ippatsu-share-pages |
| branch | cursor/photo-ledger-paired-overview-pick |

## 変更ファイル

- `portal/photo-ledger/app.js`
- `portal/photo-ledger/pack.js`
- `portal/photo-ledger/service-worker.js`
- `portal/photo-ledger/styles.css`
- `scripts/verify_photo_ledger_portal.py`
- `docs/work_logs/2026-07-29_1347_codex_photo-ledger-paired-overview-pick.md`

## 実施内容

- 伐採前の直後には採用QRを作らず、伐採後の撮影後に前後候補を
  まとめて選ぶQR札画面へ差し替えた。
- 表示順を「伐採前後、枝切り、根切り、柴前後、
  竹・つる・運搬・実費」へ変更した。
- 枝切り・根切りは折りたたみ表示を維持した。
- 公開用サービスワーカーのキャッシュ識別子を更新した。
- 公開物検証へ前後一括PICKと表示順の静的検査を追加した。

## 守った制約

- `scripts/generate_portal.py`と他のポータル生成物は変更していない。
- Supabase、業務データ、原本写真、Excelは変更していない。
- secret、ローカル絶対パスを公開物へ含めていない。
- 対象ファイルだけを明示してstageする。

## 次に必要な作業

- テスト後にPRを作成し、承認済みの公開依頼に従ってmainへ反映する。
- 公開URLと必要アセットのHTTP 200、前後一括PICKの配信を確認する。

