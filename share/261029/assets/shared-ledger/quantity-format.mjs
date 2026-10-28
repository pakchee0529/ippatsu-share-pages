export const quantityTotal=r=>(r.mode==='replace'?r.revised:r.initial)===null||r.additional===null?null:(r.mode==='replace'?r.revised:r.initial)+r.additional;
// Presentation preserves unknown values. Never use these strings as quantity input.
const publicNumber=value=>{if(value===null||value===undefined)return null;if(!Number.isFinite(value))throw Error('数量表示の形式を確認してください');return value;};
export const publicQuantityText=value=>{const n=publicNumber(value);return n===null?'未確認':String(n);};
export const publicQuantityTotal=r=>{const base=publicNumber(r.mode==='replace'?r.revised:r.initial),additional=publicNumber(r.additional);return base===null||additional===null?null:base+additional;};
export function publicHistoryText(r){const before=publicNumber(r.initial),after=publicNumber(r.mode==='replace'?r.revised:r.initial),additional=publicNumber(r.additional);let text=before===after?publicQuantityText(before):publicQuantityText(before)+'→'+publicQuantityText(after);if(additional===null){if(after!==null)text+='＋未確認';}else if(additional>0)text+='＋'+additional;return text;}
export function totalText(rows){const sum=values=>values.some(v=>v===null)?null:values.reduce((a,b)=>a+b,0),before=sum(rows.map(r=>publicNumber(r.initial))),after=sum(rows.map(publicQuantityTotal));return before===after?publicQuantityText(before):publicQuantityText(before)+'→'+publicQuantityText(after);}
