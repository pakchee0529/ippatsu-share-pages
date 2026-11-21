import {imageInput} from '../sandbox/image-input.mjs';
import {call,linkFor} from '../sandbox/api.mjs';
import {previewPage} from '../sandbox/preview.mjs';
import {surveyTemplate} from './survey-template.mjs?v=4';

const root=document.querySelector('#sandbox-tools'),form=root.querySelector('form'),field=form.elements.prompt,file=form.elements.sketch;
const log=root.querySelector('[role=log]'),status=root.querySelector('[role=status]'),attachment=root.querySelector('output');
let history=[],draft=null,target=null,photo=null,survey=false,busy=false,card=null;
function bubble(role,text){
  const row=document.createElement('div');row.className=role==='user'?'row mine':'row';
  const body=document.createElement('div');body.className='bubble';body.textContent=text;
  row.append(body);log.append(row);log.scrollTop=log.scrollHeight;return body;
}
function fresh(){
  history=[];draft=null;target=null;photo=null;survey=false;card?.remove();card=null;
}
function link(container,item){
  const a=document.createElement('a');a.href=linkFor(item.id);a.textContent=item.definition.title;container.append(a);
}
function greet(){bubble('assistant','何を作りましょう？ 現調リストなら、担当者の名前と径間名か紙の写真を送ってください。');}
greet();
file.onchange=()=>{attachment.textContent=file.files[0]?.name||'';};
async function publish(){
  if(!draft){bubble('assistant','先に作りたいページを教えてください。');return;}
  const item=await call('sandboxPublish',{draft,id:target?.id,revision:target?.revision});
  fresh();target=item;link(bubble('assistant','掲載しました。'),item);
}
async function send(text){
  if(busy)return;
  const selected=file.files[0];if(!text&&!selected)return;
  busy=true;form.querySelector('button').disabled=true;
  try{
    text=text.trim()||(survey?'この写真から径間を取り込んで':'この写真を使いたい');
    bubble('user',text+(selected?'（写真付き）':''));
    if(!selected&&/^(?:これで)?(?:掲載|公開|反映|保存)(?:して|する|お願い)?[。！! ]*$/.test(text)){await publish();return;}
    if(/^(新しい会話|最初から|やり直す)$/.test(text)){fresh();greet();return;}
    if(!selected&&/編集|修正/.test(text)&&!draft){
      const {items}=await call('sandboxList');
      const matches=items.filter(i=>text.includes(i.definition.title));
      if(matches.length===1){fresh();target=matches[0];}
      else if(!target){bubble('assistant','編集したいページの名前を添えてください。「一覧」で探せます。');return;}
    }
    if(!selected&&/一覧|開いて|を開く/.test(text)){
      const {items}=await call('sandboxList');const found=/一覧/.test(text)?items:items.filter(i=>text.includes(i.definition.title));
      const msg=bubble('assistant',found.length?'ページを選んでください。':'該当するページが見つかりません。「一覧」と送ってください。');found.forEach(i=>link(msg,i));return;
    }
    if(/新規で|新しく作|別の.*作|新しい.*作/.test(text)||(target&&!draft&&!/編集|修正/.test(text)&&/専用|作って|作成/.test(text)))fresh();
    if(selected)photo=await imageInput(selected);
    survey=survey||(!target&&/現調|径間/.test(text));
    status.textContent='いっぱつちゃんが確認中…';
    const reply=await call('sandboxDraft',{interactive:true,prompt:text,template:survey?'survey':undefined,history:history.slice(-8),previous:draft,image:photo,id:target?.id,revision:target?.revision});
    history.push({role:'user',text});
    if(reply.question){history.push({role:'assistant',text:reply.question});bubble('assistant',reply.question);return;}
    const candidate=survey?surveyTemplate(reply.survey):reply.draft;
    draft=candidate;card?.remove();card=bubble('assistant',candidate.title+' の下書き');card.append(previewPage(candidate.html));
    const btn=document.createElement('button');btn.textContent='この内容で掲載';btn.onclick=()=>send('掲載して');card.append(btn);log.scrollTop=log.scrollHeight;
  }catch(e){bubble('assistant',e.message);}
  finally{status.textContent='';field.value='';file.value='';attachment.textContent='';busy=false;form.querySelector('button').disabled=false;log.scrollTop=log.scrollHeight;}
}
form.onsubmit=e=>{e.preventDefault();send(field.value);};
