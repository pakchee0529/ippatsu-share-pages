# 261014の指定5件 詳細編集・再生成

ユーザーの明示依頼に基づく指定編集・対象日再生成・公開。

対象は日付261014、episode1、active construction_wait、順序1〜5で固定。
- 51406495 西日裏32N3～32N4: 吊り切り実費
- 51406497 西日裏32N5～32N6: 吊り切り実費
- 51406498 西日裏32N6～32N7: 吊り切り実費。ハシゴ3本、ノビル、ロープ、サシエ。
- 51402413 川又17～18: 吊り切り実費。ハシゴ4本、ノビル、ロープ、サシエ。
- 51402414 川又18～19: ハシゴ3本ノビル

全件B車不可（DB text false）、傾斜「傾」、集積（collect=true/work_method=集積）、carry_out=false維持。

## 実行・検証
完全なcases/case_detailsのbefore snapshotと保存下書きsnapshotを私有workspaceへ保管。GUI操作用node_replがこの環境では無いため、GUIと同じ既存apply_share_date_case_editサービスを完全itemで使用した。保存直前の再照合、case_details更新日時条件、許可5列以外の差分拒否を追加して保存。独立した新clientのreadbackで全件一致。casesは不変、case_detailsの指定5列と正常updated_atのみ変化。写真・数量・位置・施工回・順序・状態・warningは不変。保存下書き0件のまま、既存data/backup/.envの70ファイルはhash不変。

最新remote/会社HEAD e308c279e13b4d7356d661e2283a16449ff0ce0b を照合。別の隔離cloneで修正版GUIと同じ実生成helperを1回動かし、mode=share-update/date=261014で生成。MainWindow/業務GUIの新規起動なし。完全番号・UUID・日付の5件を固定し、順序、15数量欄、備考、B車/傾斜/集積、旧新版台帳と予定修正query、GPS URL、2点/nearby JSON、POINTSを検証。以前壊れていたP26年の見出しは2026年10月14日へ正常化。liveoverlayコードを保持。対象日以外のHTMLはbytes不変。写真保存先date/management/labelと数量queryを保持。

TOPの変更は、e308c27で既に削除・アーカイブ済みの261013への古い共有カードの除去のみ。261013のアーカイブを元に戻していない。

## 公開範囲
share/261014/index.html、portal/index.html、本作業ログのみ。生成scriptや他日付・写真・下書きは変更しない。Pages完了と公開HTML/画面、liveoverlay実効値はpush後に確認し、私有workspaceの最終結果へ記録する。
