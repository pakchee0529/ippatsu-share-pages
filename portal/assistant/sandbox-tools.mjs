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
function greet(){bubble('assistant','ここは、欲しい道具やページを自由に作って試せる砂場っす。どんなことができたら便利ですか？');}
greet();
const camera=form.elements.camera;
for(const picker of [camera,file])picker.onchange=()=>{
  const selected=picker.files[0];if(!selected)return;
  (picker===camera?file:camera).value='';attachment.textContent=selected.name;
};
async function readAttachment(f){
  if(f.type.startsWith('image/'))return {image:await imageInput(f)};
  if(/\.pdf$/i.test(f.name)){
    if(f.size>700000)throw Error('PDFは700KBまでです。必要なページだけ選んでください。');
    if(!(await f.slice(0,5).text()).startsWith('%PDF-'))throw Error('PDFを読み取れません。');
    const data=await new Promise((resolve,reject)=>{const reader=new FileReader();reader.onload=()=>resolve(reader.result);reader.onerror=()=>reject(Error('ファイルを開けません'));reader.readAsDataURL(f);});
    return {pdf:'data:application/pdf;base64,'+data.split(',')[1]};
  }
  if(/\.(txt|csv|md)$/i.test(f.name)&&f.size<=100000)return {attachmentText:await f.text()};
  throw Error('画像、PDF（700KBまで）、UTF-8のTXT・CSV・MD（100KBまで）を選んでください。');
}
async function publish(){
  if(!draft){bubble('assistant','先に作りたいページを教えてください。');return;}
  const item=await call('sandboxPublish',{draft,id:target?.id,revision:target?.revision});
  fresh();target=item;link(bubble('assistant','掲載しました。'),item);
}
async function send(text){
  if(busy)return;
  const selected=camera.files[0]||file.files[0];if(!text&&!selected)return;
  busy=true;form.querySelector('button').disabled=true;
  try{
    text=text.trim()||(survey?'この資料から径間を取り込んで':'この資料を使いたい');
    bubble('user',text+(selected?'（'+selected.name+'）':''));
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
    if(selected)photo=await readAttachment(selected);
    survey=survey||(!target&&/現調|径間/.test(text));
    status.textContent='いっぱつちゃんが確認中…';
    const reply=await call('sandboxDraft',{interactive:true,prompt:text,template:survey?'survey':undefined,history:history.slice(-8),previous:draft,...photo,id:target?.id,revision:target?.revision});
    history.push({role:'user',text});
    if(reply.question){history.push({role:'assistant',text:reply.question});bubble('assistant',reply.question);return;}
    const candidate=survey?surveyTemplate(reply.survey):reply.draft;
    draft=candidate;card?.remove();card=bubble('assistant',candidate.title+' の下書き');card.append(previewPage(candidate.html));
    const btn=document.createElement('button');btn.textContent='この内容で掲載';btn.onclick=()=>send('掲載して');card.append(btn);log.scrollTop=log.scrollHeight;
  }catch(e){bubble('assistant',e.message);}
  finally{status.textContent='';field.value='';file.value='';camera.value='';attachment.textContent='';busy=false;form.querySelector('button').disabled=false;log.scrollTop=log.scrollHeight;}
}
form.onsubmit=e=>{e.preventDefault();send(field.value);};

root.querySelector('#survey-shortcut').onclick=()=>{
  if(busy)return;
  if(field.value.trim()||camera.files.length||file.files.length||draft){field.value='新しく現調リストを作って。'+field.value;field.focus();return;}
  fresh();survey=true;
  const request='現調リストを作る',question='誰のリストにしますか？ 担当者名と、径間名か紙の写真を送ってください。';
  history.push({role:'user',text:request},{role:'assistant',text:question});
  bubble('user',request);bubble('assistant',question);field.focus();
};
