export function displayReference(text){
  return text.replace(/(^|[／/]\s*)管理番号\s*([0-9０-９]{8})(?=\s*(?:[／/]|$))/gu,'$1$2');
}
