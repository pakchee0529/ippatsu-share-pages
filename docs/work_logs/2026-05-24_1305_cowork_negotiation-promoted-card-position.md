# 作業ログ: 交渉待ちページ 昇格カード表示位置 + survey localStorage キャッシュ修正

| 項目 | 値 |
|------|----|
| Date | 2026-05-24 |
| Repo | ippatsu-share-pages |
| Branch | main（直接修正） |
| Agent | Claude Cowork |

## Purpose

スマホ E2E で発見した2つのバグを修正。

1. **表示位置バグ**: 昇格カードが交渉待ちページの全体地図の下に表示される
2. **localStorage キャッシュバグ**: revert 後に現調待ちページで 99990001 が一瞬表示後に消える

## Bug 1: 昇格カード表示位置

### Root Cause

`appendPromotedCards` が `host.insertAdjacentHTML("beforeend", html)` で
`<main>` 末尾に追記 → `<section class="map-section">` の後になる。

### Fix

`render_negotiation_immediate_status_js()` 内で `host.querySelector(".map-section")` を取得し、
`mapSection.insertAdjacentHTML("beforebegin", html)` で地図の直前に挿入。
地図セクションが存在しない場合は `beforeend` フォールバック。

## Bug 2: survey ページ localStorage キャッシュが revert 後も残る

### Root Cause

`applySurveyOverlay(statusMap)` が **サーバー結果より localStorage を優先**していた。

```javascript
// 旧コード（バグ）
var st = statusMap[key];  // サーバー: undefined（revert済）
if (localStorage.getItem(portalStatusLsKey(key)) === "negotiation_wait") {
  st = "negotiation_wait";  // ← 古いキャッシュが勝ってカードを隠す！
}
```

revert 後: DB は空 → サーバー結果 = undefined だが localStorage に
`"negotiation_wait"` が残っていたため、カードが非表示になっていた。

### Fix

`fetchPortalOverrides()` を `{ok: boolean, statusMap: {...}}` を返すよう変更。
`applySurveyOverlay(statusMap, serverOk)` にサーバー正常応答フラグを追加。

- `serverOk=true` (サーバー正常応答): サーバー結果を正とし、`negotiation_wait` でないキーの
  localStorage を清掃する
- `serverOk=false` (サーバー到達不可): localStorage をフォールバックとして使用

```javascript
// 修正後
function fetchPortalOverrides() {
  if (!PORTAL_STATUS_API_KEY) return Promise.resolve({ ok: false, statusMap: {} });
  return fetch(...)
    .then(data => data.ok ? { ok: true, statusMap: portalStatusMapFromResponse(data) }
                          : { ok: false, statusMap: {} })
    .catch(() => ({ ok: false, statusMap: {} }));
}

function applySurveyOverlay(statusMap, serverOk) {
  // serverOk=true のとき: negotiation_wait でなければ localStorage を清掃
  if (serverOk && st !== "negotiation_wait") {
    localStorage.removeItem(portalStatusLsKey(key));
  }
}

fetchPortalOverrides().then(result => {
  applySurveyOverlay(result.statusMap, result.ok);
});
```

## Changed Files

- `scripts/portal_immediate_status_client.py` — Bug 1 + Bug 2 両方の修正
- `portal/survey/index.html` — 再生成（修正反映済み）
- `portal/negotiation/index.html` — 再生成（修正反映済み）

## Verification（サンドボックス）

再生成コマンド:
```
PORTAL_SURVEY_REQUEST_API_KEY=<anon JWT> PORTAL_IMMEDIATE_STATUS=1 \
python scripts/generate_portal.py --data-root /tmp/test_data_root
```

### survey/index.html
- `PORTAL_STATUS_API_KEY`: 空でない・is_jwt=True ✅
- `fetchPortalOverrides` returns `{ok, statusMap}` ✅
- `applySurveyOverlay(result.statusMap, result.ok)` ✅
- `serverOk` branch present ✅
- `localStorage.removeItem(portalStatusLsKey` in overlay ✅
- `service_role` 実値なし（コメントのみ）✅

### negotiation/index.html
- `PORTAL_STATUS_API_KEY`: 空でない・is_jwt=True ✅
- `PROMOTED_SURVEY_CANDIDATES`: count=2 keys=['99990001','99990002'] ✅
- `mapSection.insertAdjacentHTML("beforebegin", html)` ✅
- `beforeend` フォールバック ✅
- `service_role` 実値なし（コメントのみ）✅

## スマホ E2E 期待動作

1. 現調待ちで 99990001 を「現調済みにする」→ 交渉待ちへ昇格
2. 交渉待ちページで 99990001 が地図より**上**に表示される
3. 「現調待ちに戻す」を押す → DB から削除 + localStorage 清掃予約
4. 現調待ちページを開く → 99990001 が**消えずに**表示されたまま残る
5. 99990002 も残る（未操作）
6. ページ再読み込み後も 99990001 / 99990002 が表示される

## Commit

（人間または Cursor が commit 後に記載）

## Next actions

- Cursor: lock ファイル削除後 `git add` + commit
- 人間: main push → GitHub Pages publish
- スマホ E2E: 上記手順で確認
