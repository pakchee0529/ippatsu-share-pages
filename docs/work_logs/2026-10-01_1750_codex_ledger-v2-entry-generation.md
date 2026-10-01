# 新版入口の限定再生成

- `scripts/refresh_ledger_v2_entries.py` により、260728/260827/261002の計6カードに既存/新版の入口を生成。
- `scripts/test_ledger_v2_entries.py`：フッター以外の本文がHEADと一致し、再実行で差分が増えないことを確認。
- 既存版HTML/app.jsは変更なし。新版の保存・APIは別。
- PC新ショートカットと新APIを用意し、共有リンクから利用するため公開対象とする。
