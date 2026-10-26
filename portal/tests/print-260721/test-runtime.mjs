// Test-only transport: no API endpoint or network POST. Ordinary input UI is unchanged.
const clone=x=>JSON.parse(JSON.stringify(x));
export const params=new URLSearchParams(location.search),date='260721',cs=params.get('management_no');
const data=await(await fetch('./bundle.json',{cache:'no-store'})).json();
const item=data.items.find(x=>x.document.case.management_no===cs);if(!item)throw Error('この印刷テストの3現場から選択してください');
const id=item.document.id;export const KEY='ippatsu-print-test-260721/v1:'+id;
const source={case_id:id,management_no:cs,span_label:item.label,work_date:date,design_no:'0',planned:clone(item.document.case.planned),test_only:true,test_note:item.note||'2026/7/21 仮印刷テスト'};
const entry={cs,base:clone(source.planned)};
function read(){const raw=localStorage.getItem(KEY);if(raw===null)return {case:clone(source),document:null,revision:0};const d=JSON.parse(raw);if(d.schema!=='ippatsu-print-test-save/v1'||!Number.isSafeInteger(d.revision)||d.revision<1||d.document?.id!==id||d.document.case?.case_id!==id||d.document.case?.management_no!==cs||d.document.case?.work_date!==date)throw Error('試験保存の形式が一致しません。元データを残して停止しています');return {case:clone(source),document:clone(d.document),revision:d.revision};}
export async function request(query={},body){if(query.id&&query.id!==id||query.date&&query.date!==date||query.management_no&&query.management_no!==cs)throw Error('試験対象が一致しません');if(!body)return read();if(!navigator.locks)throw Error('このブラウザは安全な端末内保存に対応していません。入力を控えて対応ブラウザで開いてください');
return navigator.locks.request(KEY,async()=>{const before=read(),d=body.document;if(body.expected_revision!==before.revision)throw Object.assign(Error('別の試験画面で更新されています。入力を保持して保存済みを再読込してください'),{status:409});if(d?.schema!=='ippatsu-photo-ledger/v2'||d.id!==id||d.case?.case_id!==id||d.case?.management_no!==cs||d.case?.work_date!==date||JSON.stringify(d.case.original_planned)!==JSON.stringify(source.planned))throw Error('試験の案件・元数量が一致しません');const previous=localStorage.getItem(KEY);if(previous!==null)localStorage.setItem(KEY+':previous',previous);const next={schema:'ippatsu-print-test-save/v1',document:clone(d),revision:before.revision+1};const text=JSON.stringify(next);localStorage.setItem(KEY,text);if(localStorage.getItem(KEY)!==text)throw Error('試験保存の読戻しが一致しません');return {saved:true,revision:next.revision};});}
export const context={...read(),entry,offline:false};
export function rememberContext(d){Object.assign(context,clone(d),{entry,offline:false});}
export function savedForPrint(){return read();}
export default {caseId:id,trialId:id,workDate:date,displayDate:date,original:clone(source.planned),revised:clone(source.planned),cuts:Object.fromEntries(Object.keys(source.planned).filter(c=>/^[EN]/.test(c)).map(c=>[c,[]])),pairs:Object.fromEntries(['BA','TK','TR','SB'].map(c=>[c,[]])),otherRefs:[]};
