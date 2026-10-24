// 26 only. Retains existing ledger-v2 JSON, revision CAS and readback.
import {config} from './config.mjs';
import {CODES,records,sameBase,unit,binding} from './read-model.mjs';
const entryFor=d=>config.cases.find(c=>c.cs===String(d.case.management_no).replace(/\D/g,''));
function initialize(d){const entry=entryFor(d);if(!entry||d.case.work_date!==config.date||!d.case.case_id||!sameBase(d.case.original_planned,entry.base))throw Error('26日の案件・付託基準を確認してください');if(!d.share_quantity_adjustments){d.share_quantity_adjustments={schema:'ippatsu-share-quantities/v1',case_id:d.case.case_id,base:{...entry.base},additional:{}};}return entry;}
export async function prepare(d){const entry=initialize(d);if(await binding(d.case.case_id)!==entry.binding||d.id!==d.case.case_id)throw Error('現在の受付と台帳の案件IDが一致しません');for(const code of CODES){const n=d.case.planned[code];if(!Number.isSafeInteger(n)||n<0||n>1000000)throw Error(code+' の変更後数量を確認してください');}const ext=d.share_quantity_adjustments;if(ext.schema!=='ippatsu-share-quantities/v1'||ext.case_id!==d.case.case_id||!sameBase(ext.base,entry.base))throw Error('変更追加の基準版が一致しません');for(const [code,n] of Object.entries(ext.additional)){if(!CODES.includes(code)||!Number.isSafeInteger(n)||n<0||n>1000000)throw Error(code+' の追加数量を確認してください');}if(d.clearanceM!==undefined&&d.clearanceM!==null&&(!Number.isFinite(d.clearanceM)||d.clearanceM<0||Math.abs(d.clearanceM*10-Math.round(d.clearanceM*10))>1e-8))throw Error('離隔は0以上・小数1桁までです');return d;}
export function render({document:d,persist,render,save,say}){
 const entry=entryFor(d);if(!entry||!d.case.case_id)return;
 const host=document.querySelector('#plan-fields');if(!host)return;
 try{initialize(d);}catch(e){say(e.message,true);return;}
 const ext=d.share_quantity_adjustments;
 for(const code of CODES){
   const input=host.querySelector('[data-path="case.planned.'+code+'"]');if(!input)continue;
   input.min='0';input.step='1';input.required=true;input.addEventListener('input',()=>queueMicrotask(()=>{if(input.value===''){d.case.planned[code]=null;persist();}const extra=host.querySelector('[data-share-additional="'+code+'"]');if(extra&&!Object.hasOwn(ext.additional,code)){try{extra.value=records(entry.base,d).find(r=>r.code===code).additional;}catch{extra.value='';}}}));const label=input.closest('label');
   const hint=document.createElement('small');hint.textContent='付託基準 '+entry.base[code]+unit(code)+' ／ 上の欄は変更後';label.append(hint);
   const wrap=document.createElement('span');wrap.className='share-additional';wrap.style.display='block';wrap.textContent='追加 '+unit(code)+(/^[EN]/.test(code)?'（写真本数から自動・修正可）':'');
   const added=document.createElement('input');added.type='number';added.min='0';added.step='1';added.required=Object.hasOwn(ext.additional,code);let inferred=0;try{inferred=records(entry.base,d).find(r=>r.code===code).additional;}catch{inferred='';}added.value=Object.hasOwn(ext.additional,code)?(ext.additional[code]??''):inferred;added.placeholder='写真本数を確認';added.dataset.shareAdditional=code;added.setAttribute('aria-label',code+' 追加 '+unit(code));
   added.addEventListener('input',e=>{e.stopPropagation();ext.additional[code]=added.value===''?null:Number(added.value);added.required=true;persist();});
   wrap.append(added);label.append(wrap);
 }
 const ba=document.querySelector('#section-BA');if(ba){const label=document.createElement('label');label.textContent='離隔（現場1欄・m）';const input=document.createElement('input');input.type='number';input.min='0';input.step='0.1';input.value=d.clearanceM??'';input.dataset.shareClearance='1';input.addEventListener('input',e=>{e.stopPropagation();d.clearanceM=input.value===''?null:Number(input.value);persist();});label.append(input);ba.append(label);}
 const old=document.querySelector('#old-link');if(old)old.hidden=true;
 document.querySelector('#share-26-return')?.remove();const nav=document.createElement('p');nav.id='share-26-return';
 const button=document.createElement('button');button.type='button';button.className='secondary';button.textContent='保存して共有ページへ戻る';button.onclick=async()=>{button.disabled=true;try{if(await save())location.href='../../share/261026/#case-'+entry.cs;}finally{button.disabled=false;}};
 const back=document.createElement('a');back.href='../../share/261026/#case-'+entry.cs;back.textContent='保存せず共有へ戻る';nav.append(button,document.createTextNode(' '),back);document.querySelector('#cloud-save').parentElement.append(nav);
}
