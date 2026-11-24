export const allWaiting=/^(?:現調|現場調査)待ち(?:の(?:案件|現場|径間))?(?:を|の)?(?:全件|全部)(?:で|を)?(?:お願い|表示|作成|出して|見せて)?[。！!]?$/u;
export function requestedWaiting(text){
  text=text.trim().replace(/だけ(?:で)?[。！!]?$/u,"");
  if(allWaiting.test(text))return {scope:'all'};
  if(/^[A-Za-zＡ-Ｚａ-ｚ]?[\p{Script=Han}々ヶケぁ-んァ-ヶー]{1,32}$/u.test(text) && /[\p{Script=Han}ァ-ヶ]/u.test(text)
     && !/担当|お願い|全部|全件|現調|リスト|径間|管理番号|設計番号|して|したい|ほしい|さん$/u.test(text)){
    return {scope:'crown',crown:text};
  }
}
