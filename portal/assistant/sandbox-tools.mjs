import {imageInput} from '../sandbox/image-input.mjs';
import {call,linkFor} from '../sandbox/api.mjs';
import {previewPage} from '../sandbox/preview.mjs';
import {surveyTemplate} from './survey-template.mjs?v=fieldcopy1';

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
  let failed=false;busy=true;form.querySelector('button').disabled=true;
  try{
    text=text.trim()||(survey?'この資料から径間を取り込んで':'この資料を使いたい');
    bubble('user',text+(selected?'（'+selected.name+'）':''));
    if(!selected&&/^(?:現場の)?進入(?:路|口)(?:写真)?を登録(?:したい|する|して)?[。！! ]*$/.test(text)){entranceGuide();return;}
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
    draft=candidate;card?.remove();card=bubble('assistant',candidate.title+' の下書き');if(reply.survey?.notes?.length){const note=document.createElement('p');note.textContent='送った資料と見比べてほしい径間が'+reply.survey.notes.length+'件あります。';card.append(note);}card.append(previewPage(candidate.html));
    if(reply.survey?.numbers?.length){
      const label=document.createElement('label'),box=document.createElement('input');box.type='checkbox';
      label.append(box,'読み取った番号をリストに載せる（'+reply.survey.numbers.length+'件）');
      const examples=document.createElement('details'),heading=document.createElement('summary');heading.textContent='径間ごとの番号を見る';examples.append(heading);
      for(const n of reply.survey.numbers){const row=document.createElement('div');row.textContent=n.name+'　'+n.text;examples.append(row);}
      card.append(label,examples);box.onchange=()=>{draft=surveyTemplate(reply.survey,box.checked);card.querySelector('iframe').replaceWith(previewPage(draft.html));};
    }
    const btn=document.createElement('button');btn.textContent=target?'共有ページに保存':'砂場にページを追加';btn.onclick=()=>send('掲載して');card.append(btn);log.scrollTop=log.scrollHeight;
  }catch(e){failed=true;bubble('assistant',e.message==='Failed to fetch'?'送れませんでした。書いた内容とファイルは残っています。そのまま「送信」を押してください。':e.message);}
  finally{status.textContent='';if(!failed){field.value='';file.value='';camera.value='';attachment.textContent='';}busy=false;form.querySelector('button').disabled=false;log.scrollTop=log.scrollHeight;}
}
function entranceGuide() {
  const message=bubble('assistant','設計番号か径間名で現場を探してね。写真はまとめて選べるよ。入口から歩く順に並べて、曲がり角や分岐には写真ごとに矢印を描いてね。');
  const search=document.createElement('form'); search.className='entrance-search';
  const input=document.createElement('input');
  input.type='search'; input.placeholder='設計番号または径間名'; input.required=true;
  input.setAttribute('aria-label','設計番号または径間名');
  const submit=document.createElement('button');submit.textContent='探す';
  const results=document.createElement('div');results.setAttribute('aria-live','polite');
  const trial=document.createElement('a');trial.href='../sandbox/entrance/?mode=try';trial.textContent='写真で矢印を試す（保存なし）';
  search.append(input,submit);message.append(search,results,trial);
  search.onsubmit=async event=>{
    event.preventDefault();
    const q=input.value.trim();if(!q)return;
    submit.disabled=true;results.textContent='検索中…';
    try {
      const response=await fetch('https://evmgsqdrojxppxknrzfk.supabase.co/functions/v1/field-entrance',{
        method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({action:'cases',q}),signal:AbortSignal.timeout(15000)
      });
      if(!response.ok)throw Error();
      const {cases}=await response.json();
      results.textContent=cases.length?'写真を登録する現場を選んでください。':'該当する現場がありません。径間名の一部でも探せます。';
      for(const item of cases){
        const link=document.createElement('a');
        link.href='../sandbox/entrance/?'+new URLSearchParams({mode:'register',case_id:item.id,q});
        link.textContent=item.label+' ／ 設計番号 '+(item.design_number||'未登録')+(item.episode_no?' ／ 受付'+item.episode_no+'回目':'');
        results.append(link);
      }
    }catch{results.textContent='検索できませんでした。「探す」で再試行できます。';}
    finally{submit.disabled=false;}
  };
  input.focus();
}
root.querySelector('#entrance-shortcut').onclick=()=>{
  bubble('user','進入路を登録'); entranceGuide();
};
form.onsubmit=e=>{e.preventDefault();send(field.value);};

root.querySelector('#survey-shortcut').onclick=()=>{
  if(busy)return;
  if(field.value.trim()||camera.files.length||file.files.length||draft){field.value='新しく現調リストを作って。'+field.value;field.focus();return;}
  fresh();survey=true;
  const request='現調リストを作る',question='誰のリストにしますか？ 担当者名と、径間名か紙の写真を送ってください。';
  history.push({role:'user',text:request},{role:'assistant',text:question});
  bubble('user',request);bubble('assistant',question);field.focus();
};
