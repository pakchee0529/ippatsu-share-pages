export function surveyRequest(text) {
  const cleaned = text.trim().replace(/[。！!？?]+$/u, '');
  const match = cleaned.match(/^(.*?)(?:現調|現場調査)(?:に(?:行く|いく)|用|する)?(?:の|用の)?(?:径間|現場)?(?:の)?(?:リスト|一覧)(?:を|が)?(?:新しく|新規で)?(?:新規作成|作りたい|作って(?:ほしい|ください)?|作る|作成(?:したい|して|する)?|つく(?:って|りたい|る)|ほしい)(?:です|んやけど|ねん|くれる|もらえる)?(?:[、,：:\s]+(.+))?$/u);
  if (!match) return null;
  return [match[1].replace(/(?:だけで|から|で|の)$/u, '').trim(), match[2]].filter(Boolean).join(' ');
}
export function numberInput(text) {
  const cleaned = text.normalize('NFKC').trim().replace(/^管理番号[\s:：]*/u, '');
  const numbers = cleaned.split(/[\s、,;；・]+/u);
  return numbers.every(value => /^\d{8}$/.test(value)) ? numbers : undefined;
}
export function spanInputs(text) {
  // 横並びの番号と径間は原票の同一行として照合する。独立した入力だけを分割する。
  const rows = text.trim().split(/[\r\n、,，;；]+/u).map(row => row.trim()).filter(Boolean);
  const number = /^\d{8}$/u;
  const span = /^(?=[^\s]+$)(?=.*\d)[\p{L}\d._・-]+[~〜][\p{L}\d._・-]+$/u;
  const normalized = rows.map(row => row.normalize('NFKC'));
  return normalized.some(row => span.test(row)) && normalized.every(row => span.test(row) || number.test(row))
    ? rows : undefined;
}
