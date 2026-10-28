import {compatiblePublishedBase} from './published-basis.mjs?v=20261028-allocation19';
// Validated, per-case browser snapshot. No credentials or automatic submission.
export const cacheKey=(date,cs)=>'ippatsu-shared-ledger-context/v1:'+date+':'+cs;
export const pendingKey=(date,cs)=>cacheKey(date,cs)+':pending';
export function validateContext(data,entry,date,cs){
 if(!entry||entry.cs!==cs||!data?.case||!/^[0-9a-f-]{36}$/i.test(data.case.case_id||'')||data.case.management_no.replace(/\D/g,'')!==cs||data.case.work_date!==date||!compatiblePublishedBase(data.case.planned,entry.base))throw Error('現在の案件・予定日・数量基準を確認してください');
 if(!Number.isSafeInteger(data.revision)||data.revision<0||data.document===null&&data.revision!==0||data.document!==null&&(!data.document||data.document.id!==data.case.case_id||data.document.case?.case_id!==data.case.case_id))throw Error('保存版と台帳の状態が一致しません。入力を保全して確認してください');return data;
}
export function readContext(storage,date,cs){try{const c=JSON.parse(storage.getItem(cacheKey(date,cs))||'null');if(c?.version!==1||c.date!==date||c.cs!==cs)return null;validateContext(c.data,c.entry,date,cs);return c;}catch{return null;}}
export function writeContext(storage,data,entry,date,cs){validateContext(data,entry,date,cs);const value=JSON.stringify({version:1,date,cs,entry,data});storage.setItem(cacheKey(date,cs),value);if(storage.getItem(cacheKey(date,cs))!==value)throw Error('オフライン用の案件情報を保全できません');}
export const networkFailure=e=>e instanceof TypeError||['AbortError','TimeoutError'].includes(e?.name)||e?.status>=500;
export async function resolveContext({storage,date,cs,online,load,timeoutMs=1500}){const cached=readContext(storage,date,cs);if(!online){if(!cached)throw Error('この案件はオフライン準備がありません。通信できる場所で一度開いてください');return {...cached.data,entry:cached.entry,offline:true};}try{let timer;const loaded=cached?await Promise.race([load(),new Promise((_,reject)=>{timer=setTimeout(()=>reject(Object.assign(Error('通信確認が遅いため端末の保存版を開きます'),{name:'TimeoutError'})),timeoutMs);})]).finally(()=>clearTimeout(timer)):await load();const {data,entry}=loaded;validateContext(data,entry,date,cs);let cacheError='';try{writeContext(storage,data,entry,date,cs);}catch(e){cacheError=e.message;}return {...data,entry,offline:false,cacheError};}catch(e){if(!cached||!networkFailure(e))throw e;return {...cached.data,entry:cached.entry,offline:true};}}
export function markPending(storage,date,cs,caseId){const value=JSON.stringify({caseId,date,cs});storage.setItem(pendingKey(date,cs),value);if(storage.getItem(pendingKey(date,cs))!==value)throw Error('保存結果の確認用情報を端末に保全できません');}
export function hasPending(storage,date,cs,caseId){try{return JSON.parse(storage.getItem(pendingKey(date,cs))||'null')?.caseId===caseId;}catch{return true;}}
export const clearPending=(storage,date,cs)=>storage.removeItem(pendingKey(date,cs));
