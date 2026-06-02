# 作業ログ: survey 上部件数を表示カード数に同期

| 項目 | 値 |
|------|----|
| 日時 | 2026-05-29 20:00 |
| 担当 | cursor |
| repo | ippatsu-share-pages |
| branch | main（未 commit） |

## 変更ファイル

- `scripts/generate_portal.py`
- `scripts/portal_immediate_status_client.py`
- `portal/survey/index.html`（survey-only 再生成）

## 実施内容

- `#survey-visible-count` / `#survey-count-lead`（候補総数 data 属性）を追加
- `isSurveyCardVisible` / `getVisibleSurveyCardCount` / `updateSurveyVisibleCount`
- `applySurveyMultipinState` 内で件数とマルチピンを同時更新
- `syncSurveyCardVisibility` 経由で overlay・操作後も反映

## 守った制約

- portal/index/archive/negotiation 未変更
- push 未実施

## 次に必要な作業

- 人間確認後 commit: `Sync survey visible count with cards`
