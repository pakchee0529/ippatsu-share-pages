# share 260611 組み替え 公開（2026-06-10）

## 背景

ippatsu-pc Supabase apply 後、260611 を玉置山171～180 の6件（51405340〜348）に差し替え。傾斜・現場効率に基づく人間指定順。

## 変更ファイル

| ファイル | 内容 |
|----------|------|
| `share/260611/index.html` | 2件→**6件**（51405219/397 除去、51405340〜348 追加） |
| `portal/index.html` | portal-top-only 再生成（min-date=**260611** 維持、260611 **6件**表示） |

## コマンド

```powershell
# ippatsu-pc 側で生成・コピー後
cd C:\Users\kotan\Projects\ippatsu-share-pages
python scripts/generate_portal.py --mode portal-top-only --portal-min-date 260611
```

## 表示順（share/260611）

1. 51405340 玉置山171～172
2. 51405344 玉置山175～176
3. 51405345 玉置山176～177
4. 51405346 玉置山177～178
5. 51405347 玉置山178～179
6. 51405348 玉置山179～180

## HTML 確認

| 項目 | 結果 |
|------|------|
| article.card 件数 | 6 |
| `#share-map` / `initShareMultipinMap` | あり |
| POINTS | 6点・0,0 なし |
| 51405219 / 51405397 | share/260611 から除去 |
| portal TOP 260611 件数 | **6件** |
| portal min-date | 260611 |
| archive | 未変更 |

## 未変更

- share/260612 / share/260610
- portal/archive/
- Supabase（本 repo では write なし）

## 参照

ippatsu-pc apply ログ: `docs/work_logs/2026-06-10_share_schedule_260611_reorg_apply.md`
