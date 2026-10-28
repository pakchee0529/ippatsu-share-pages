import {publishedSource} from './published-basis.mjs?v=20261029-r10';
import {resolveContext,validateContext,writeContext} from './offline-context.mjs?v=20261029-r10';
// Existing normal ledger API only. Never imports a trial fixture or demo storage.
export const API='https://evmgsqdrojxppxknrzfk.supabase.co/functions/v1/photo-ledger-v2';
export const params=new URLSearchParams(location.search),date=params.get('date'),cs=params.get('management_no');
export async function request(query,body){const response=await fetch(API+'?'+new URLSearchParams(query),{method:body?'POST':'GET',headers:body?{'Content-Type':'application/json'}:undefined,body:body?JSON.stringify(body):undefined,cache:'no-store',signal:AbortSignal.timeout(20000)});const data=await response.json();if(!response.ok)throw Object.assign(Error(data.message||'台帳を読取り・保存できません'),{status:response.status,data});return data;}
if(!/^\d{6}$/.test(date||'')||!/^\d{8}$/.test(cs||''))throw Error('日付・管理番号を共有ページから指定してください');
export const context=await resolveContext({storage:localStorage,date,cs,online:navigator.onLine!==false,load:async()=>{
const page=await fetch('../../share/'+date+'/',{cache:'no-store',signal:AbortSignal.timeout(20000)});if(!page.ok)throw Error('共有ページの数量根拠を読めません');
const html=await page.text(),match=html.match(/<script id="shared-ledger-config" type="application\/json">([\s\S]*?)<\/script>/);if(!match)throw Error('この日の正式な新版台帳接続はまだ生成されていません');
const published=JSON.parse(match[1]),entry=published.cases.find(x=>x.cs===cs);if(!entry)throw Error('共有対象の案件ではありません');
const data=await request({date,management_no:cs});
data.case=publishedSource(data.case,entry);return {data,entry};}});
const entry=context.entry;
export function rememberContext(data){validateContext(data,entry,date,cs);Object.assign(context,data,{offline:false});try{writeContext(localStorage,data,entry,date,cs);context.cacheError='';}catch(e){context.cacheError=e.message;}}
const codes=Object.keys(entry.base),native=context.document;
const fixture={caseId:context.case.case_id,trialId:context.case.case_id,workDate:date,displayDate:date,original:{...entry.base},revised:{...entry.base},cuts:Object.fromEntries(codes.filter(c=>/^[EN]/.test(c)).map(c=>[c,[]])),pairs:Object.fromEntries(['BA','TK','TR','SB'].map(c=>[c,[]])),otherRefs:[]};
export default fixture;
