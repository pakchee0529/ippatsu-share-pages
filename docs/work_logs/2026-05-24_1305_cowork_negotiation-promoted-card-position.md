# 作業ログ: 交渉待ちページ 昇格カード表示位置修正

| 項目 | 値 |
|------|----|
| Date | 2026-05-24 |
| Repo | ippatsu-share-pages |
| Branch | main（直接修正） |
| Agent | Claude Cowork |

## Purpose

スマホ E2E 中に発見したバグ修正。

現調待ちから昇格した案件（portal_case_status_overrides overlay）が
交渉待ちページで「全体地図の下」に表示されていた。

期待: 既存の交渉待ちカード群と同じエリア（全体地図より上）に表示する。

## Root Cause

`appendPromotedCards` 関数が `host.insertAdjacentHTML("beforeend", html)` で
`<main>` の末尾に追記していた。

`<main>` の構造:
```
<main>
  <article class="card negotiation-card">  ← 静的カード
  <section class="map-section">           ← 全体地図
</main>
```

`beforeend` で追記すると `<section class="map-section">` の後ろになる。

## Fix

修正箇所: **`scripts/portal_immediate_status_client.py`** の `render_negotiation_immediate_status_js()`
（generate_portal.py がインポートして portal/negotiation/index.html を生成するテンプレートソース）

`appendPromotedCards` 内で `host.querySelector(".map-section")` で地図セクションを取得し、
`mapSection.insertAdjacentHTML("beforebegin", html)` で地図の直前に挿入するよう変更。

地図セクションが存在しない場合は従来通り `beforeend` にフォールバック。

## Changed Files

- `scripts/portal_immediate_status_client.py` — `appendPromotedCards` 生成テンプレートの挿入位置修正
- `portal/negotiation/index.html` — `PORTAL_SURVEY_REQUEST_API_KEY` + テスト queue で再生成（修正反映済み）

## Verification（サンドボックス）

再生成コマンド:
```
PORTAL_SURVEY_REQUEST_API_KEY=<anon JWT> \
PORTAL_IMMEDIATE_STATUS=1 \
python scripts/generate_portal.py --data-root /tmp/test_data_root
```
（`/tmp/test_data_root/survey/queue.json` = `docs/examples/immediate_status_test_queue.json`）

確認結果:
- `PORTAL_STATUS_API_KEY`: 空でない・is_jwt=True ✅
- `PROMOTED_SURVEY_CANDIDATES`: count=2 keys=['99990001', '99990002'] ✅
- `mapSection = host.querySelector(".map-section")` 存在 ✅
- `mapSection.insertAdjacentHTML("beforebegin", html)` 存在 ✅
- `beforeend` フォールバック 存在 ✅
- `service_role` 実値なし（コメント文のみ）✅
- `sb_secret_` / `SUPABASE_ACCESS_TOKEN` 実値なし ✅
- revert ボタン（`data-negotiation-revert`）・`revert_to_survey_wait` API 呼び出し維持 ✅

## スマホ E2E 手順

1. 現調待ちページで 99990001 を「現調済みにする」
2. 交渉待ちページを開く
3. 99990001 が全体地図より**上**の交渉待ちカード一覧エリアに表示される
4. 「現調待ちに戻す」で 99990001 が消える
5. 現調待ちページに 99990001 が戻る

## Commit

（人間または Cursor が commit 後に記載）

## Next actions

- Cursor: commit 後に hash をこのログに追記
- 人間: main push → GitHub Pages publish（承認後）
- スマホ E2E: 上記手順で表示位置確認
