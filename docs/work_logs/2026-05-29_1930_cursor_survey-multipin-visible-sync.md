# 作業ログ: survey 下部マルチピンを表示カードと同期

| 項目 | 値 |
|------|----|
| 日時 | 2026-05-29 19:30 |
| 担当 | cursor |
| repo | ippatsu-share-pages |
| branch | main（未 commit） |

## 変更ファイル

- `scripts/generate_portal.py`
- `scripts/portal_immediate_status_client.py`
- `portal/survey/index.html`（survey-only 再生成）

## 実施内容

- `applySurveyMultipinState` / `collectVisibleSurveyMultipinPoints` を追加
- カードに `data-multipin-lat` / `data-multipin-lng` を付与
- 固定 `var points` 初期化を廃止し、表示中カードのみ marker 再描画
- overlay / 現調済み / 返却候補成功後に `syncSurveyCardVisibility` でマルチピン更新

## 守った制約

- portal/index/archive/negotiation 未変更
- prod queue / Supabase / data/share 未変更
- push 未実施

## 次に必要な作業

- 人間確認後 commit: `Sync survey multipin with visible cards`
