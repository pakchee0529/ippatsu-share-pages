export const quantityTotal=r=>(r.mode==='replace'?r.revised:r.initial)===null||r.additional===null?null:(r.mode==='replace'?r.revised:r.initial)+r.additional;
// Lossy public presentation only. Never use these strings as quantity input.
const publicNumber=value=>{if(value===null||value===undefined)return 0;if(!Number.isFinite(value))throw Error('数量表示の形式を確認してください');return value;};
export const publicQuantityText=value=>String(publicNumber(value));
export const publicQuantityTotal=r=>publicNumber(r.mode==='replace'?r.revised:r.initial)+publicNumber(r.additional);
export function publicHistoryText(r){const before=publicNumber(r.initial),after=publicNumber(r.mode==='replace'?r.revised:r.initial);let text=before===after?String(before):before+'→'+after;if(r.additional>0)text+='＋'+r.additional;return text;}
export function totalText(rows){const before=rows.reduce((n,r)=>n+publicNumber(r.initial),0),after=rows.reduce((n,r)=>n+publicQuantityTotal(r),0);return before===after?String(before):before+'→'+after;}
