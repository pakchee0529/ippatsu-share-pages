import {workingStatus} from './working.mjs';
import {imageInput} from '../sandbox/image-input.mjs';
import {call,linkFor} from '../sandbox/api.mjs?v=activity1';
import {previewPage} from '../sandbox/preview.mjs';
import {surveyTemplate} from './survey-template.mjs?v=fieldcopy1';
import {appearance} from '../sandbox/appearance.mjs';
import {account} from '../account/session.mjs';

const root=document.querySelector('#sandbox-tools'),form=root.querySelector('form'),field=form.elements.prompt,file=form.elements.sketch;
const log=root.querySelector('[role=log]'),status=root.querySelector('[role=status]'),attachment=root.querySelector('output');
const work=workingStatus(status);
let activity;
function step(label){
  if(!activity){
    activity=document.createElement('details');
    const heading=document.createElement('summary');
    activity.append(heading,document.createElement('ol'));
    log.append(activity);
    activity.style.cssText='margin:.5rem 1rem;color:var(--muted);font-size:.875rem';
  }
  const list=activity.lastElementChild;
  if(list.lastElementChild?.textContent!==label){
    const item=document.createElement('li');item.textContent=label;list.append(item);
  }
  activity.firstElementChild.textContent='作業履歴（'+list.children.length+'件）';
  work.show(label);
}

let history=[],draft=null,target=null,photo=null,survey=false,busy=false,card=null;
let previousVersion=null;
let pendingDraft=null,pendingPublication=null,recoveryButton=null;
const retryWords=/^(?:結果(?:を)?(?:もう一度)?(?:読み直して|読み直す|読んで|再確認して)|(?:もう一度|もう一回)(?:試して|読み直して|お願い)?|再試行(?:して)?)[。！!？?\s]*$/;
function clearRecovery(){recoveryButton?.remove();recoveryButton=null;}
function bubble(role,text){
  const row=document.createElement('div');row.className=role==='user'?'row mine':'row';
  const body=document.createElement('div');body.className='bubble';body.textContent=text;
  row.append(body);log.append(row);log.scrollTop=log.scrollHeight;return body;
}
function fresh(){
  previousVersion=null;
  pendingDraft=null;pendingPublication=null;clearRecovery();
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
  if(pendingPublication){await checkPublication();return;}
  if(!draft){bubble('assistant','先に作りたいページを教えてください。');return;}
  const prior={draft,id:target?.id,revision:target?.revision};
  try{
    step('砂場に掲載しています');
    const item=await call('sandboxPublish',{draft,id:target?.id,revision:target?.revision});
    if(!item?.id||!item.definition)throw Error('掲載結果を受け取れませんでした。');
    fresh();target=item;link(bubble('assistant','掲載しました。'),item);
  }catch(e){
    if(e.status && e.status<500 && e.status!==408)throw e;
    pendingPublication=prior;
    const msg=bubble('assistant','掲載の返事を受け取れませんでした。掲載済みのページを確認できます。');
    recovery(msg,'掲載結果を確認','publishCheck');
  }
}
function recovery(message,label,key){
  clearRecovery();const btn=document.createElement('button');btn.type='button';btn.dataset[key]='';btn.textContent=label;
  btn.onclick=()=>send('結果を読み直して');message.append(document.createElement('br'),btn);recoveryButton=btn;
}
async function checkPublication(){
  step('掲載結果を照合しています');
  const prior=pendingPublication;
  const {items}=prior.id ? {items:[await call('sandboxGet',{id:prior.id})]} : await call('sandboxList');
  const content=html=>String(html??'').replace(/<!--ippatsu-style:[\w-]+:[\w-]+-->/g,'');
  const matches=items.filter(item=>item?.definition?.title===prior.draft.title &&
    content(item.definition.html)===content(prior.draft.html) &&
    (!prior.id||item.id===prior.id&&item.revision>prior.revision));
  if(matches.length===1){fresh();target=matches[0];link(bubble('assistant','同じ内容の掲載済みページを確認できました。'),target);return;}
  const msg=bubble('assistant',matches.length?'同じ内容のページが複数あります。確認したいページを選んでください。':'まだ掲載結果を特定できません。時間をおいてもう一度確認できます。');
  matches.forEach(item=>link(msg,item));recovery(msg,'掲載結果を確認','publishCheck');
}
function draftPreview(html){
  const panel=document.createElement('dialog');
  panel.className='draft-preview';
  panel.open=true;
  panel.setAttribute('aria-label','下書きのプレビュー');
  const toggle=document.createElement('button');
  toggle.type='button';toggle.textContent='大きく見る';
  function collapse(){
    panel.close();panel.open=true;
    toggle.textContent='大きく見る';toggle.focus();
  }
  toggle.onclick=()=>{
    if(panel.matches(':modal')){collapse();return;}
    panel.close();panel.showModal();toggle.textContent='チャットに戻る';
  };
  panel.oncancel=event=>{event.preventDefault();collapse();};
  panel.append(toggle,previewPage(html));return panel;
}
async function generate(job){
  try{
    step('依頼内容を準備しています');
    if(!job.payload){
      if(job.file)step('添付ファイルを読み込んでいます');
      const asset=job.file?await readAttachment(job.file):photo;
      job.asset=asset;
      job.payload={interactive:true,prompt:job.text,template:survey?'survey':undefined,history:history.slice(-8),previous:draft,...asset,id:target?.id,revision:target?.revision};
    }
    step(job.payload.template==='survey'?'現調リストを準備しています':draft||target?'下書きを更新しています':'下書きを作っています');
    const reply=await call('sandboxDraft',job.payload,step);
    step('受け取った回答を確認しています');
    if(typeof reply?.question==='string'&&reply.question.trim()){
      history.push({role:'user',text:job.text},{role:'assistant',text:reply.question});
      photo=job.asset;bubble('assistant',reply.question);
    }else{
      if(job.payload.template==='survey'&&(!reply?.survey||typeof reply.survey.title!=='string'))throw Error('現調リストの下書きを受け取れませんでした。');
      const candidate=job.payload.template==='survey'?surveyTemplate(reply.survey):reply?.draft;
      if(!candidate?.title||typeof candidate.html!=='string'||!candidate.html.trim())throw Error('下書きの内容を確認できませんでした。');
      step('下書きのプレビューを組み立てています');
      previousVersion=draft&&card?{draft,card,history:history.slice(),photo}:null;
      draft=candidate;card?.remove();card=bubble('assistant',candidate.title+' の下書き');if(reply.survey?.notes?.length){const note=document.createElement('p');note.textContent='送った資料と見比べてほしい径間が'+reply.survey.notes.length+'件あります。';card.append(note);}card.append(draftPreview(candidate.html));
      if(reply.survey?.numbers?.length){
        const label=document.createElement('label'),box=document.createElement('input');box.type='checkbox';
        label.append(box,'読み取った番号をリストに載せる（'+reply.survey.numbers.length+'件）');
        const examples=document.createElement('details'),heading=document.createElement('summary');heading.textContent='径間ごとの番号を見る';examples.append(heading);
        for(const n of reply.survey.numbers){const row=document.createElement('div');row.textContent=n.name+'　'+n.text;examples.append(row);}
        card.append(label,examples);box.onchange=()=>{draft=surveyTemplate(reply.survey,box.checked);card.querySelector('iframe').replaceWith(previewPage(draft.html));};
      }
      const choices=document.createElement('div');choices.className='suggestions';
      const options={
        pin:['番号を見やすくして','チェック欄を大きくして','地図を上に置いて'],
        check:['行全体をタップしてチェック','未チェックを上にして','項目を追加できるようにして'],
        calculator:['入力例を見せて','単位を分かりやすくして','結果を大きくして'],
        calendar:['今日を目立たせて','日付で絞り込めるようにして','予定を追加しやすくして']
      };
      const ideas=/ゲーム|遊び|得点/.test(job.text+candidate.title)?['操作の練習を付けて','難しさを選べるようにして','もう一度遊びやすくして']:options[appearance(candidate).icon]||['文字を見やすくして','入力例を付けて','よく使う操作を上にして'];
      for(const idea of ideas){const button=document.createElement('button');button.type='button';button.textContent=idea;button.onclick=()=>send(idea);choices.append(button);}
      card.append(choices);
      if(previousVersion){
        const undo=document.createElement('button');undo.textContent='一つ前に戻す';card.append(undo);
        undo.onclick=()=>{if(busy||!previousVersion)return;const old=previousVersion;previousVersion=null;card.remove();draft=old.draft;card=old.card;history=old.history;photo=old.photo;const row=document.createElement('div');row.className='row';row.append(card);log.append(row);card.querySelector('[data-undo]')?.remove();pendingDraft=null;clearRecovery();};
        undo.dataset.undo='';
      }
      const btn=document.createElement('button');btn.textContent=target?'共有ページに保存':'砂場にページを追加';btn.onclick=()=>send('掲載して');card.append(btn);
      history.push({role:'user',text:job.text});photo=job.asset;
    }
    pendingDraft=null;clearRecovery();return true;
  }catch(e){
    pendingDraft=job;
    const msg=bubble('assistant',(e.message==='Failed to fetch'?'通信が途中で切れました。':e.message)+' 入力と添付は残っています。');
    recovery(msg,'同じ内容でもう一度試す','draftRetry');return false;
  }
}
async function send(text,fromComposer=false){
  if(busy)return;
  const selected=camera.files[0]||file.files[0];if(!text&&!selected)return;
  const initialField=field.value,hadText=Boolean(text.trim());
  if(fromComposer)field.value='';
  let failed=false,consumeFile=true;busy=true;form.querySelector('button').disabled=true;
  try{
    text=text.trim()||(survey?'この資料から径間を取り込んで':'この資料を使いたい');
    const previousAttempt=pendingDraft?.text===text&&pendingDraft.file===(selected||null);
    if(retryWords.test(text)||previousAttempt){
      consumeFile=selected===(pendingDraft?.file||undefined);
      if(pendingPublication)await checkPublication();
      else if(pendingDraft)failed=!await generate(pendingDraft);
      else if(card){card.scrollIntoView({block:'nearest'});bubble('assistant','直前の下書きを確認できます。');}
      else bubble('assistant','ここには読み直す下書きや掲載結果がまだありません。作りたいものを送ってください。');
      return;
    }
    bubble('user',text+(selected?'（'+selected.name+'）':''));
    if(!selected&&/^(?:現場の)?進入(?:路|口)(?:写真)?を登録(?:したい|する|して)?[。！! ]*$/.test(text)){entranceGuide();return;}
    if(!selected&&/^(?:これで)?(?:掲載|公開|反映|保存)(?:して|する|お願い)?[。！! ]*$/.test(text)){
      if(pendingDraft){bubble('assistant','直前の下書きがまだできていません。「同じ内容でもう一度試す」で確認してください。');return;}
      await publish();return;
    }
    if(/^(新しい会話|最初から|やり直す)$/.test(text)){fresh();greet();return;}
    const createRequest=/作って|作りたい|作成|作る|つくって/.test(text);
    if(!selected&&!createRequest&&/編集|修正/.test(text)&&!draft){
      step('砂場のページを探しています');
      const {items}=await call('sandboxList');
      const matches=items.filter(i=>text.includes(i.definition.title));
      if(matches.length===1){fresh();target=matches[0];}
      else if(!target){bubble('assistant','編集したいページの名前を添えてください。「一覧」で探せます。');return;}
    }
    if(!selected&&!createRequest&&(/^(?:ページの?)?一覧(?:を(?:見せて|表示して))?[。！!\s]*$/.test(text)||/(?:を開いて|を開く)[。！!\s]*$/.test(text))){
      step('砂場のページを探しています');
      const {items}=await call('sandboxList');const found=/一覧/.test(text)?items:items.filter(i=>text.includes(i.definition.title));
      const msg=bubble('assistant',found.length?'ページを選んでください。':'該当するページが見つかりません。「一覧」と送ってください。');found.forEach(i=>link(msg,i));return;
    }
    if(/新規で|新しく作|別の.*作|新しい.*作/.test(text)||(target&&!draft&&!/編集|修正/.test(text)&&/専用|作って|作成/.test(text))||(survey&&createRequest&&/ゲーム/.test(text)&&!/現調|径間/.test(text)))fresh();
    const soloPhoto=!hadText&&selected?.type.startsWith('image/')&&!draft&&!history.length;
    survey=survey||(!target&&(/現調|径間/.test(text)||soloPhoto));
    pendingDraft=null;clearRecovery();
    failed=!await generate({text,file:selected||null});
  }catch(e){failed=true;const msg=bubble('assistant',e.message==='Failed to fetch'?'通信できませんでした。時間をおいてもう一度試してください。':e.message);
    if(pendingPublication)recovery(msg,'掲載結果を確認','publishCheck');
  }
  finally{if(failed&&fromComposer&&!field.value)field.value=initialField;activity=null;work.clear();if(!failed){
    if(consumeFile&&(camera.files[0]||file.files[0])===selected){file.value='';camera.value='';attachment.textContent='';}
  }busy=false;form.querySelector('button').disabled=false;log.scrollTop=log.scrollHeight;}
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
form.onsubmit=e=>{e.preventDefault();send(field.value,true);};

root.querySelector('#survey-shortcut').onclick=()=>{
  if(busy)return;
  if(field.value.trim()||camera.files.length||file.files.length){fresh();survey=true;send('新しく現調リストを作って。'+field.value.trim(),true);return;}
  fresh();survey=true;
  const name=account()?.name?.trim();
  const request='現調リストを作る',question=name?name+'さんの現調リストを作ります。径間名か紙の写真を送ってください。別の方の分なら、その方の名前も添えてください。':'誰のリストにしますか？ 担当者名と、径間名か紙の写真を送ってください。';
  history.push({role:'user',text:request},{role:'assistant',text:question});
  bubble('user',request);bubble('assistant',question);field.focus();
};
