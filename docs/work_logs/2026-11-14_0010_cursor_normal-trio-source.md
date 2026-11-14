# 作業ログ: 通常の日次3画面経路と空欄規則

担当: cursor / 単独 writer。2026-11-14 UTC。branch: cursor/source-blank-zero-20261113。
本人の限定訂正・恒久対策・公開指示を適用。会社PC/HDD、業務DB、保存台帳、receipt、予定は未操作。
正本スキル ippatsu-align-generation 全文と operation-contract / route-record / evidence-history / publication、ippatsu-build-daily-pages 全文と input-and-checks を本人指定後に再読し適用。スキル読取り自体を表示受入と同一視しない。
対象は11/16〜20、23案件、日別3/3/5/6/6、51407008は火曜のみ。現行公開PR47と原公開PR45の公開情報を限定投影。
Library画像は実視認したが公開画面でありCS/付託原本ではない。保存済み参照先の検索で当該原本は取得できず、今回実参照して確認した原典空欄0、実数量の0訂正0。108非該当候補・94未知を一括0認定していない。
規則は原典の数量欄を実参照して空欄と確認した場合だけ0、未参照/判読不能/矛盾は未確認。CS/付託種別・hash・頁・案件/径間・数量fieldを束縛。非数量欄は対象外。検査用根拠は架空の合成fixtureであり、実原本確認の証拠ではない。

根因: 前回生成器はtemplatesだけを流用し、apply_saved_ledger_views.transformと通常readability後処理を通さず、別views-readonly制御と説明文を入れた。dailyファイル配信検査だけでは正本経路・通常導線の受入にならなかった。
修正経路: 公開済み限定入力→PC通常HTML renderer→正式transform(source_entries明示)→通常readability/カードfooter→通常views.mjsのsourceOnly分岐→共通renderProjection→3画面。閲覧限定でAPI/編集/保存/完了handlerは起動しない。通常保存経路のguardは維持。
日次離隔表の全体入口と案件footer、指示書入口を通常部品で生成。利用画面から指定外の根拠説明を除去し数量/未知状態は非表示属性に維持。測定離隔は根拠未取得なので未確認を保持。
公開用の空欄訂正metadataは空配列。原本・私有観測JSONを公開せず、将来確認済空欄の限定投影のみhash付きmetadataに残し通常再生成でも保持。manifestは正当な生成元/5資産/15画面/投影metadataを一組で再検証、guardの拒否を緩めない。
検査: semantic8、合成投影6、PC根拠8合格。同一入力反復byte一致。345数量の値/状態は旧公開と一致(108候補/53原典正値/90既存正式カテゴリ/94未知)。15画面とTOP、全23案件、日付/順序/火曜限定一致。通常回帰: transport25、bushcard14、寸法24+45268+21+11、archive scope9、空予定・TOP非表示・見出し合格。
隔離Chromium: PC1280/スマホ390で5日3画面と全23指示書を実クリック。余計な説明なし、日次離隔表リンク到達、外部通信なし。印刷38種81頁、空末尾/見出し孤立/表分割/overflow失敗0。外部地図は遮断した隔離検査であり実描画の証拠ではない。
従来Git地図コード/URL/23案件結合を保持。先の通常ブラウザで証明書警告があったため回避・設定変更・再試行なし。地図実描画/操作、実紙印刷、会社GUI/EXE採用は未確認。TOP/他日/archiveは不変。公開は別生成物commitと同一PRにまとめ承認範囲で実施予定。
