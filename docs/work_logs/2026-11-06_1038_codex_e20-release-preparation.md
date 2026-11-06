# E20独立群再計算の公開準備（未公開）

- 基準main: f061f4e72ab5869ceba1584a2bba1dd6e0136c53。2026-11-06 01:38:52 UTC にorigin/main不変を再確認。
- 隔離ブランチ: cursor/e20-independent-refresh-20261106。commit/push/公開なし。
- 内容: CUTS群が有効なら独立SB/TK/TRエラー中もCUTSのみ更新。保存時の全体整合は維持。旧linked未完成・アンカー不一致は値を保持して停止、正常移行は保存可能。adapterの全write入口で完成検査。
- SBの一時保存仕様は本人指示により保留、変更していない。
- 世代: 20261106-e20-independent-r1。shared-ledger各import、input.html、SW、bootstrap、SOURCE-HASHES、通常生成元ASSET_VERSIONを整合。
- 既存bootstrapだけ20261104キャッシュを確認する不整合を修正。SW動作自体やcache削除方針は変更せず。
- share/261104・261105・261106の計9入口を既存transformで隔離再生成。旧版→新版の文字列置換以外の差分0を検査。固定archiveと本番業務値は未変更。
- 合成検査: E20/旧linked/180ケース回帰、adapter保存・読戻し、SB寸法45268網羅、24例/21不正/11統合、SBカード14例が成功。配布候補そのものへE20全試験も実行。
- bundle検査: 58importがSWの同世代exact URLに存在。SOURCE-HASHES整合。SW模擬では新URLが新operations、旧URLは旧cache、未知版503。旧cache削除なし。
- 既存test_saved_schedule_carry.mjsは元から古いconfig版20261026-carry1を直接importし、TR配列も欠落するfixture。既存test自体は未変更。別隔離コピーの版/fixtureだけ更新した9ケースは成功。これを既存test原文の成功とは報告しない。
- 実ブラウザ、新規SW install/activate、配信HTTP bytes、実サーバー保存は未検査。

## 公開ゲート
1. 公開承認・並行作業の占有を確認。mainが進んだら再baseして差分と全試験を再実行。
2. 部品2点だけで公開しない。新版adapterと新版operations・参照graph・SWを同じcommitに含める。
3. input pending表示改善はこの候補に含めない。別採用時は追加検査とSW asset登録が必要。
4. 正式反映直前にmain・対象blob、業務値無変更、9入口の版以外無変更、archive不変を再確認。
5. 承認済みbranch/PR手順で公開後、CIと実URLのハッシュ、import、旧/新タブ挙動を確認。ユーザー下書きを消去・強制更新しない。

## 復旧計画
不具合なら新規更新を止め、データを変更せず対象差分のみを基準mainから戻す候補を作る。後続無関係commitを巻き戻さない。既存新cacheが残るため、旧ファイルを単に戻すだけで全端末復旧とはしない。復旧専用の新世代タグで基準実装・全import・SW・hash・生成入口を一組として再生成、同じ配布検査後に承認済み手順で公開する。下書き保全を確認してからユーザーへ再読込を案内。既存cache/端末保存の強制削除はしない。

## 公開承認後の最終確認
本人がE20候補のポータル反映と実画面確認を明示承認。親担当が同repoの他公開作業なしを確認。main f061f4e不変、全差分は承認候補と一致。最終回帰・bundle/SW模擬・SB網羅・compileall・diff checkが成功。実画面・実サーバー保存は未検証のまま、業務入力の代行や下書き消去は行わない。branch/PRから承認対象を反映し配信を照合する。
