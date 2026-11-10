import {canonicalQuantity} from './quantity-kinds.mjs?v=20261110-transport-r1';
export const prefix=id=>'instruction-base-correction:'+id+':';
export const keyFor=(id,revision,tab)=>prefix(id)+revision+':tab:'+tab;
export function persistProposal(storage,key,value){const data={kind:'instruction-base-correction-proposal',...value},text=JSON.stringify(data);storage.setItem(key,text);const got=JSON.parse(storage.getItem(key));if(canonicalQuantity(got)!==canonicalQuantity(data))throw Error('修正案の読戻し不一致');return data;}
export function proposals(storage,id){const out=[];for(let i=0;i<storage.length;i++){const key=storage.key(i);if(!key?.startsWith(prefix(id)))continue;try{const value=JSON.parse(storage.getItem(key));if(value?.kind==='instruction-base-correction-proposal'&&value.id===id)out.push({key,...value});}catch{/* Keep corrupt bytes; never clear another draft. */}}return out;}
