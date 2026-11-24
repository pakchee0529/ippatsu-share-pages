import {call} from './api.mjs';
import {localInstruction,matchesTarget,fontSize} from './local-instruction.mjs';
const page=location.pathname.split('/').filter(Boolean).filter(p=>p!=='index.html').at(-1);
const nodes=[...document.querySelectorAll('[data-edit-part]')];
const endpoint='https://evmgsqdrojxppxknrzfk.supabase.co/functions/v1/ippatsu-assistant';
let current;
function apply(state){
  if(current&&current.revision>state.revision)return;
  for(const el of nodes){
    const fields=state.settings[el.dataset.editPart];if(!fields)continue;
    if(fields.text)el.textContent=fields.text;
    if(fields.size)el.style.fontSize=fields.size+'px';
  }
  current=state;
}
async function read(){
  const res=await fetch(endpoint,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({action:'sandboxReadAppearance',page})});
  if(!res.ok)throw Error('表示設定を読み込めませんでした。');apply(await res.json());
}
const launch=document.createElement('button');launch.type='button';launch.textContent='いっぱつちゃんに相談';launch.style.cssText='min-height:40px;margin:.25rem .5rem';
const dialog=document.createElement('dialog');dialog.style.cssText='width:min(90vw,30rem);box-sizing:border-box';
dialog.innerHTML='<form><strong>このページの表示を編集</strong><p>例：「タイトルを大きくして」</p><label>変えたいところ <select></select></label><p><input aria-label="編集の依頼" placeholder="タイトルを大きくして" maxlength="200"></p><p role="status"></p><button>送信</button> <button type="button" data-apply hidden>反映する</button> <button type="button" data-close>閉じる</button></form>';
const nav=document.querySelector('main nav,header nav,nav');
if(nav)nav.append(launch);else document.querySelector('h1')?.after(launch);
document.body.append(dialog);
const form=dialog.querySelector('form'),select=form.querySelector('select'),input=form.querySelector('input'),status=form.querySelector('[role=status]'),commit=form.querySelector('[data-apply]');
let pending;
function reset(){pending=null;commit.hidden=true;}
launch.onclick=async()=>{reset();status.textContent='';dialog.showModal();try{await read();select.replaceChildren(new Option('依頼から選ぶ',''),...nodes.map(el=>new Option(el.textContent.trim(),el.dataset.editPart)));}catch(e){status.textContent=e.message;}};
form.querySelector('[data-close]').onclick=()=>dialog.close();input.oninput=select.onchange=reset;
form.onsubmit=async e=>{
 e.preventDefault();reset();if(!current)return;
 const chosen=nodes.find(el=>el.dataset.editPart===select.value);
 const text=input.value.trim();let parsed=localInstruction(text)||(chosen&&localInstruction('「'+chosen.textContent.trim()+'」を'+text));
 let proposed;
 if(!parsed){
   const first=input.value;
   try{
     status.textContent='変更案を考えています…';
     const plan=await call('sandboxPlanAppearance',{page,prompt:text,selected:select.value,fields:nodes.map(el=>({key:el.dataset.editPart,label:el.textContent.trim().slice(0,160),size:Math.round(fontSize(el))}))});
     if(input.value!==first||select.value!==(chosen?.dataset.editPart||'')||!dialog.open)return;
     if(plan.property==='question'){status.textContent=plan.value;return;}
     proposed=nodes.find(el=>el.dataset.editPart===plan.field);
     if(!proposed||(chosen&&chosen!==proposed)||!['size','text'].includes(plan.property)){status.textContent='変更する項目を一つ選んでください。';return;}
     parsed={target:proposed.textContent.trim(),property:plan.property,value:plan.value};
     if(plan.property==='size'){
       const size=Number(plan.value);if(!Number.isInteger(size)||size<12||size>48)throw Error('文字サイズを12～48pxで指定してください。');
       parsed.delta=size-Math.round(fontSize(proposed));
     }
   }catch(e){status.textContent=e.message;return;}
 }
 const targets=matchesTarget(nodes,parsed.target);
 const el=proposed||(chosen&&targets.includes(chosen)?chosen:!chosen&&targets.length===1?targets[0]:null);
 if(!el){status.textContent='対象を一つ選んで、変更内容を指定してください。';return;}
 const value=parsed.property==='size'?Math.max(12,Math.min(48,Math.round(fontSize(el))+parsed.delta)):parsed.value;
 pending={field:el.dataset.editPart,property:parsed.property,value,revision:current.revision};status.textContent='「'+el.textContent.trim()+'」を '+value+(parsed.property==='size'?'px':'')+' に変更します。';commit.hidden=false;
};
commit.onclick=async()=>{if(!pending||commit.disabled)return;commit.disabled=true;try{
 const result=await call('sandboxEditAppearance',{page,...pending});apply(result);reset();status.textContent='保存しました。';
}catch(e){status.textContent=e.message;}finally{commit.disabled=false;}};
read().catch(()=>{});
