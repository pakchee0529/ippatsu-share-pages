# 台帳変更・指示書修正

台帳上部は施工数量の変更（変更前/変更後/差分）。指示書の修正は有効元数を置換し、受領raw元数・過去revisionは保全する。追加内訳・純減は従来のまま。旧correctionsは自動移行しない。既存変更後の元数修正は未確定につき当該操作を停止。

公開main795660a0を基準に通常生成元のASSET_VERSIONとSW/依存を統一。既存Git raw日別HTMLへ正規transformを実行し、inline数量config・地図script・数量セル・条件を保持。API version2は無変更。既存互換readerを先に採用するまで公開/実データ移行を保留。

隔離candidateのJS/Python/実PYZ module/HTML/PC handler/API fixture検査を継承。実ブラウザ・実Excel/PDF・本番DBは未実施。詳細証跡は私有 ledger-format-candidate-20261105 と ledger-format-adoption-20261105。Refs #12（自動closeなし）。
