# 共有ポータルTOPのHallmark適用候補

基点は公開mainの `6937861a6e869f5000e8f93d024de1d89532c4a3`。
TOP専用の生成スタイルをFurrowに変更。既存の予定区分の色は値を保ったままCSS変数化した。

`portal-top-only` で生成前後のスタイルを照合。採用元HTMLのスタイル外はバイト一致を確認した。
表示対象は3カード。既存の退役済み入口の再出現検査と `git diff --check` は成功。
Hallmark静的検査はFAIL 0件。説明メタデータの既存警告が1件あり、ブラウザ検査はpuppeteer-core不在で未実施。

対象は生成コードとTOP HTML。公開は既存の担当者が行う。
