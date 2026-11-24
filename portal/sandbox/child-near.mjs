export function nearbyIntent(text){
  return /近[く場い]|周辺|近所|付近/u.test(text)&&/追加|足し|足す|入れ|候補|探し|探す|探せ/u.test(text);
}
export function nearbyChoice(text){
  const choice=text.normalize('NFKC').trim().match(/^([1-9])(?:番(?:目)?)?(?:で|を)?(?:お願い(?:します)?|追加(?:して)?|にして)?[。!！]?$/u);
  return choice?Number(choice[1]):null;
}
export function listCase(row){
  let id=row.key?.match(/^span-case-([\da-f-]{36})$/i)?.[1];
  if(!id&&/^c-[\w-]{22}$/.test(row.key)){
    const hex=Array.from(atob(row.key.slice(2).replace(/-/g,'+').replace(/_/g,'/')),s=>s.charCodeAt(0).toString(16).padStart(2,'0')).join('');
    id=[hex.slice(0,8),hex.slice(8,12),hex.slice(12,16),hex.slice(16,20),hex.slice(20)].join('-');
  }
  const number=String(row.reference||'').normalize('NFKC').match(/(?:^|管理番号\s*)(\d{8})(?=\s*(?:[／/]|$))/)?.[1];
  return {name:row.name,...(id&&{case_id:id}),...(number&&{management_no:number})};
}
