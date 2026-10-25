// Existing normal ledger API only. Never imports a trial fixture or demo storage.
export const API='https://evmgsqdrojxppxknrzfk.supabase.co/functions/v1/photo-ledger-v2';
export const params=new URLSearchParams(location.search),date=params.get('date'),cs=params.get('management_no');
export async function request(query,body){const response=await fetch(API+'?'+new URLSearchParams(query),{method:body?'POST':'GET',headers:body?{'Content-Type':'application/json'}:undefined,body:body?JSON.stringify(body):undefined,cache:'no-store',signal:AbortSignal.timeout(20000)});const data=await response.json();if(!response.ok)throw Error(data.message||'台帳を読取り・保存できません');return data;}
if(!/^\d{6}$/.test(date||'')||!/^\d{8}$/.test(cs||''))throw Error('日付・管理番号を共有ページから指定してください');
const page=await fetch('../../share/'+date+'/',{cache:'no-store'});if(!page.ok)throw Error('共有ページの数量根拠を読めません');
const html=await page.text(),match=html.match(/<script id="shared-ledger-config" type="application\/json">([\s\S]*?)<\/script>/);if(!match)throw Error('この日の正式な新版台帳接続はまだ生成されていません');
const published=JSON.parse(match[1]),entry=published.cases.find(x=>x.cs===cs);if(!entry)throw Error('共有対象の案件ではありません');
const data=await request({date,management_no:cs});
if(!data.case||data.case.management_no.replace(/\D/g,'')!==cs||data.case.work_date!==date||Object.entries(entry.base).some(([c,n])=>n===null||data.case.planned[c]!==n))throw Error('現在の案件・予定日・数量基準を確認してください');
if(!Number.isSafeInteger(data.revision)||data.revision<0||data.document===null&&data.revision!==0)throw Error('保存版と台帳の状態が一致しません。入力を保全して確認してください');
export const context={...data,entry,date,cs};
const codes=Object.keys(entry.base),native=data.document;
const fixture={caseId:data.case.case_id,trialId:data.case.case_id,workDate:date,displayDate:date,original:{...entry.base},revised:{...entry.base},cuts:Object.fromEntries(codes.filter(c=>/^[EN]/.test(c)).map(c=>[c,[]])),pairs:Object.fromEntries(['BA','TK','TR','SB'].map(c=>[c,[]])),otherRefs:[]};
export default fixture;
