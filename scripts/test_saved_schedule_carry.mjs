import assert from 'node:assert/strict';
const version='20261026-carry1',dir=new URL('../portal/shared-ledger/',import.meta.url);
globalThis.document={querySelector:()=>({textContent:'{"date":"261027"}'})};
const {config}=await import(new URL('config.mjs?v='+version,dir));
const {project,CODES}=await import(new URL('read-model.mjs',dir));
const {toNative,fromNative}=await import(new URL('native-adapter.mjs',dir));
const {writeContext,resolveContext}=await import(new URL('offline-context.mjs',dir));
const id='00000000-0000-4000-8000-000000000001',base=Object.fromEntries(CODES.map(c=>[c,1]));
const source={case_id:id,management_no:'90000001',span_label:'合成試験1～2',work_date:'261027',planned:base};
const entry={cs:'90000001',base};
const native={schema:'ippatsu-photo-ledger/v2',id,case:{...source,work_date:'261026',original_planned:base},cuts:{},pairs:{},selected:[],transport:[],special:[],adjustments:[]};
const saved={document:native,revision:1},original=JSON.stringify(saved);let count=0;
for(const day of ['261027','261028']){config.date=day;const p=await project(entry,{...source,work_date:day},saved);assert.equal(p.document.case.work_date,'261026');assert.match(p.message,/引継ぎ/);count++;}
config.date='261027';
for(const change of [d=>d.case.case_id='00000000-0000-4000-8000-000000000002',d=>d.case.management_no='90000002',d=>d.case.work_date='261332',d=>d.case.original_planned={...base,E10:99}]){const d=JSON.parse(JSON.stringify(saved));change(d.document);await assert.rejects(()=>project(entry,source,d));count++;}
config.date='261026';await assert.rejects(()=>project(entry,source,saved));count++;config.date='261027';
const ui={schema:'ippatsu-photo-ledger-ui/3',trialId:id,revision:2,records:CODES.map(code=>({code,initial:1,mode:'unchanged',revised:null,additional:0})),pairs:{SB:[]},cuts:{E10:[{id:'test',date:'261026',no:'001',count:1}]},special:{US:[]},adjustments:[],selected:['E10'],clearanceM:null};
const next=toNative(ui,native,source);assert.equal(next.case.work_date,'261027');assert.equal(next.cuts.E10[0].date,'261026');assert.equal(fromNative(next,source,2,()=>{}).cuts.E10[0].count,1);count++;
const m=new Map(),storage={getItem:k=>m.get(k)??null,setItem:(k,v)=>m.set(k,v)};
writeContext(storage,{case:source,document:native,revision:1},entry,'261027','90000001');
const offline=await resolveContext({storage,date:'261027',cs:'90000001',online:false,load:()=>{throw Error('must not fetch');}});assert.equal(offline.document.case.work_date,'261026');count++;
assert.equal(JSON.stringify(saved),original);console.log(JSON.stringify({passed:count,productionPosts:0,savedInputUnchanged:true}));
