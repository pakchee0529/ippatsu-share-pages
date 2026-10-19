# 写真台帳 新版: 弱回線時の静的資材 cache fallback

- 日時: 2026-10-20 07:07–07:20 JST
- 担当: Codex
- repo: ippatsu-share-pages
- 基準: main `c55bc8b39d5a75a60b7bc218c915b667a05f9c91`
- branch: `cursor/ledger-v2-sw-fallback-20261020`
- ユーザーの本番適用依頼に基づき、独立レビューGO後に本変更3ファイルを一括適用する。作成時の記録と公開後の観測は区別する。

## 目的・合格基準

正常な既存cacheがある静的app shellは、弱回線でnetworkが止まっても1要求につき約2秒で利用可能にする。cacheのない初回アクセス、API、保存、認証、案件データの契約を変えない。HTML・JSの世代/URLキーを維持し、HTTPエラーや途中で壊れたbodyで正常cacheを上書きしない。

## 変更ファイル

- `portal/ledger-v2/sw.js`
- `scripts/test_ledger_v2_sw.mjs`（新規の合成回帰）
- 本作業ログ（新規）

## 実装

- 既存6つのprecache URLに対象を限定。`app.js` と `app.js?v=20261005-1` は別キーを維持し、navigateは従来どおり `index.html` に正規化。
- app/index/model/styleは変更していないため、cache世代 `ippatsu-ledger-v2-20261005-2` を維持。fallbackはこの世代の同一requestに対する正常応答に限定し、別世代/別cacheは参照しない。
- 正常cacheがある場合だけ、network完了と2秒timerを競合させる。HTTP失敗、network拒否、body読取失敗は正常cacheへ戻す。
- `fetch()`の200ヘッダだけで成功としない。正常cacheが存在する小さい許可済み静的資材だけ、cloneのbody読了を待って元Responseを返す。元ResponseのURL/header semanticsを保持する。cacheなしはbodyを事前bufferせず元networkの待機/失敗をそのまま扱う。
- 遅れて成功したnetwork/bodyは `waitUntil` 内で同じキーを更新。cloneを先に取得し、cache容量/読取障害は健全なnetwork応答を失敗扱いにしない。timerは決着時に解除。
- `skipWaiting` はprecache完了後のみ実行。`clients.claim` もactivateの `waitUntil` に含める。
- scope外、他origin、POST、Range、未許可query、API/案件JSONはintercept/cacheしない。manifest等のprecache外資材は通常network経由になる。

## 実行した確認

- `node --check portal/ledger-v2/sw.js`: pass
- `node scripts/test_ledger_v2.mjs`: pass（実UI module compile、domain smoke、写真範囲/一括補正、実費写真枚数）
- `node scripts/test_ledger_v2_sw.mjs`: 43件 pass
  - healthy cache / cacheなし / 不正cache / 別世代
  - slow response、200ヘッダ後のbody停止、body破断、遅延成功/拒否
  - 404/500/503、cache read/write障害、timer後始末、waitUntil
  - URLキー分離、navigate正規化、API/POST/origin/scope/Range除外
  - install成功/失敗、activate cleanupとclaim
- dotクラウドの標準ChromiumでローカルHTTP fixtureを用いた実Service Worker試験: 15件 pass。実app/index/model/styleは基準コミットのまま。CSPで外部API通信を禁止し、管理番号等は合成値のみ。
  - 原本SWは2,300ms経過後も待機する負例を再現。
  - 200ヘッダ後のbody停止でも約2,004msでfallbackし、遅いbody完了後のcache更新を確認。
  - body破断、HTTP503、cacheなしの実エラー/2.7秒遅延応答、API非cacheを確認。
  - precacheの一部がHTTP503で失敗しても、旧active workerと既存cacheが維持されることを確認。
  - 既存SWからの更新で既存cache/表示中の入力が保持されることを確認。
  - network切断相当の接続断で、実フォームと端末下書き復元を確認。
  - HTML/app/model/styleそれぞれ8秒遅延でも、順次module取得を含め約6.04秒で実フォームと下書きを復元。
- `index.html`、`app.js`、`model.js`、`style.css`、`manifest.webmanifest` のGit blob SHAが基準コミットと一致することを検証。

## 守った制約・未確認範囲

- GUI、API/DB、保存処理、認証、業務データ、生成スクリプト、他のポータル/共有ページは未変更。`full generate` は実行していない。
- 会社PC/家PC、認証情報、実案件データ、本番APIへの接続なし。ローカル合成試験のみ。
- Android実機/iOS Safari、本番Pages配信、実案件の読み書きはこの作成段階では未確認。
- これは静的資材の読み込み改善。API読込待ち・初回cacheなし・写真台帳全体の新機能/PC連携を完成させる変更ではない。
- 初回更新はオンラインでSWが取得・正常installされる必要がある。cache timeoutは要求ごとであり、全画面が必ず2秒以内になる保証ではない。
- 将来app shellを変更する際は、従来どおりcache世代・versioned app URLを一緒に管理する。

## 公開前後の確認

- 本ログ・SW・回帰試験のみを同一コミットに含める。
- 基準以降のmain差分を再確認し、レビュー後に許可された公開経路で適用。
- 公開commit SHA/Pages buildと実配信SWのbytes/hashを照合。必要ならSWのみを基準版へ戻せるよう基準を保持。
