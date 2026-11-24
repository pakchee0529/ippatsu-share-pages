import {usesAttachedPhoto} from '../sandbox/attached-photo.mjs';
import {surveyRequest,numberInput,spanInputs} from './survey-create.mjs?v=ids1';
import {allWaiting,requestedWaiting} from './survey-waiting.mjs';
import {displayReference,resizeReference} from '../sandbox/reference.mjs?v=waiting1';
import {attachCamera} from './camera.mjs?v=native1';
import {packCheckpoint,unpackCheckpoint} from './checkpoint.mjs';
import {literalEdit,targetedEdit} from './short-edits.mjs?v=local2';
import {preserveBehavior,projectHistory} from './behavior-history.mjs?v=photo5';
import {numberedChoices,resolveChoice} from './choices.mjs?v=short1';
import {basicCounter} from './basic-counter.mjs';
import {checkStartup,checkLabel} from './sandbox-check.mjs?v=photo5';
import {workingStatus} from './working.mjs';
import {imageInput} from '../sandbox/image-input.mjs?v=bounded1';
import {call,linkFor} from '../sandbox/api.mjs?v=attached1';
import {previewPage} from '../sandbox/preview.mjs?v=attached1';
import {surveyTemplate} from './survey-template.mjs?v=waiting1';
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
const createSurvey=new URLSearchParams(location.search).get("create")==="survey";
let checkpointKey, checkpointStore,renderInfo={};
async function selectCheckpoint(){
  const user=account(), token=user?.token||sessionStorage.getItem('ippatsu.chat.session');
  if(!token){checkpointKey=null;return;}
  const bytes=await crypto.subtle.digest('SHA-256',new TextEncoder().encode(token));
  checkpointKey='ippatsu.chat.work.'+Array.from(new Uint8Array(bytes),b=>b.toString(16).padStart(2,'0')).join('');
  if(createSurvey)checkpointKey+='.create-survey';
  checkpointStore=user?.remember?localStorage:sessionStorage;
}
function checkpoint(job=null){
  if(!checkpointKey)return;
  try{
    if(!draft&&!history.length&&!job&&!pendingPublication){checkpointStore.removeItem(checkpointKey);return;}
    checkpointStore.setItem(checkpointKey,packCheckpoint({history:history.slice(-10),draft,target:target&&{id:target.id,revision:target.revision},survey,photo,job,pendingPublication,renderInfo,previous:previousVersion&&{draft:previousVersion.draft,history:previousVersion.history,photo:previousVersion.photo,info:previousVersion.info}}));
  }catch{status.textContent='この端末に続きを保存できませんでした。';}
}
const retryWords=/^(?:結果(?:を)?(?:もう一度)?(?:読み直して|読み直す|読んで|再確認して)|(?:もう一度|もう一回)(?:試して|読み直して|お願い)?|再試行(?:して)?)[。！!？?\s]*$/;
function clearRecovery(){recoveryButton?.remove();recoveryButton=null;}
function bubble(role,text){
  const row=document.createElement('div');row.className=role==='user'?'row mine':'row';
  const body=document.createElement('div');body.className='bubble';body.textContent=text;
  row.append(body);log.append(row);log.scrollTop=log.scrollHeight;return body;
}
function fresh(){
  previousVersion=null;
  if(checkpointKey)checkpointStore.removeItem(checkpointKey);
  pendingDraft=null;pendingPublication=null;clearRecovery();
  history=[];draft=null;target=null;photo=null;survey=false;card?.remove();card=null;
}
function link(container,item){
  const a=document.createElement('a');a.href=linkFor(item.id);a.textContent=item.definition.title;container.append(a);
}
function greet(){bubble('assistant','ここは、欲しい道具やページを自由に作って試せる砂場っす。どんなことができたら便利ですか？');}
if(!createSurvey)greet();
let captured=null;
attachCamera(root.querySelector('#sandbox-camera'),picture=>{
  captured=picture;file.value='';attachment.textContent=picture.name;
});
file.onchange=()=>{if(file.files[0]){captured=null;attachment.textContent=file.files[0].name;}};
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
    pendingPublication=prior;checkpoint();
    step('砂場に掲載しています');
    const item=await call('sandboxPublish',{draft,id:target?.id,revision:target?.revision});
    if(!item?.id||!item.definition)throw Error('掲載結果を受け取れませんでした。');
    fresh();target=item;link(bubble('assistant','掲載しました。'),item);
  }catch(e){
    if(e.status && e.status<500 && e.status!==408){pendingPublication=null;checkpoint();throw e;}
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
  let matches=items.filter(item=>item?.definition?.title===prior.draft.title &&
    content(item.definition.html)===content(prior.draft.html) &&
    (!prior.id||item.id===prior.id&&item.revision>prior.revision));
  if(prior.draft.photo){
    const full=prior.id?matches:await Promise.all(matches.map(item=>call('sandboxGet',{id:item.id})));
    matches=full.filter(item=>item.definition.photo===prior.draft.photo);
  }
  if(matches.length===1){fresh();target=matches[0];link(bubble('assistant','同じ内容の掲載済みページを確認できました。'),target);return;}
  const msg=bubble('assistant',matches.length?'同じ内容のページが複数あります。確認したいページを選んでください。':'まだ掲載結果を特定できません。時間をおいてもう一度確認できます。');
  matches.forEach(item=>link(msg,item));recovery(msg,'掲載結果を確認','publishCheck');
}
function draftPreview(html,photo){
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
  panel.append(toggle,previewPage(html,null,null,photo));return panel;
}
function renderCandidate(candidate,reply,request){
      renderInfo={reply:{survey:reply.survey,choices:reply.choices,message:reply.message},request};
      draft=candidate;card?.remove();card=bubble('assistant',candidate.title+' の下書き');
      if(reply.survey?.notes?.length){const note=document.createElement('p');note.textContent='送った資料と見比べてほしい径間が'+reply.survey.notes.length+'件あります。';card.append(note);}
      const auditNotice=typeof reply.survey?.auditNotice==='string'?reply.survey.auditNotice.trim():'';
      if(auditNotice){
        const note=document.createElement('p');
        note.dataset.surveyAudit='';
        note.textContent='参考：'+auditNotice;
        card.append(note);
      }
      if(candidate.photo){const note=document.createElement('p');note.textContent='掲載すると、この添付写真もページに表示されます。';card.append(note);}
      card.append(draftPreview(candidate.html,candidate.photo));
      if(reply.message && reply.message.trim()!==auditNotice){const note=document.createElement('p');note.textContent=reply.message;card.append(note);}
      if(reply.survey?.numbers?.length){
        const label=document.createElement('label'),box=document.createElement('input');box.type='checkbox';box.checked=new DOMParser().parseFromString(candidate.html,'text/html').querySelector('[data-reference-number]')!==null;
        label.append(box,'管理番号・設計番号をリストに表示（'+reply.survey.numbers.length+'件）');
        const examples=document.createElement('details'),heading=document.createElement('summary');heading.textContent='径間ごとの番号を見る';examples.append(heading);
        for(const n of reply.survey.numbers){const row=document.createElement('div');row.textContent=n.name+'　'+displayReference(n.text);examples.append(row);}
        card.append(label,examples);box.onchange=()=>{draft=surveyTemplate(reply.survey,box.checked);card.querySelector('iframe').replaceWith(previewPage(draft.html));checkpoint();};
      }
      const choices=document.createElement('div');choices.className='suggestions';
      const options={
        pin:['番号を見やすくして','チェック欄を大きくして','地図を上に置いて'],
        check:['行全体をタップしてチェック','未チェックを上にして','項目を追加できるようにして'],
        calculator:['入力例を見せて','単位を分かりやすくして','結果を大きくして'],
        calendar:['今日を目立たせて','日付で絞り込めるようにして','予定を追加しやすくして']
      };
      const ideas=reply.choices??(/ゲーム|遊び|得点/.test(request+candidate.title)?['操作の練習を付けて','難しさを選べるようにして','もう一度遊びやすくして']:options[appearance(candidate).icon]||['文字を見やすくして','入力例を付けて','よく使う操作を上にして']);
      for(const idea of ideas){const button=document.createElement('button');button.type='button';button.textContent=idea;button.onclick=()=>send(idea);choices.append(button);}
      card.append(choices);
      if(previousVersion){
        const undo=document.createElement('button');undo.textContent='一つ前に戻す';card.append(undo);
        undo.onclick=()=>{if(busy||!previousVersion)return;const old=previousVersion;previousVersion=null;card.remove();draft=old.draft;card=old.card;history=[...old.history,{role:'assistant',text:'利用者が直前の変更を取り消して、この下書きに戻しました。次の依頼はこの版から続けます。'}];photo=old.photo;renderInfo=old.info;const row=document.createElement('div');row.className='row';row.append(card);log.append(row);card.querySelector('[data-undo]')?.remove();pendingDraft=null;clearRecovery();checkpoint();};
        undo.dataset.undo='';
      }
      const btn=document.createElement('button');btn.textContent=target?'共有ページに保存':'砂場にページを追加';btn.onclick=()=>send('掲載して');card.append(btn);
}
async function generate(job){
  try{
    step('依頼内容を準備しています');
    if(!job.payload){
      if(job.file)step('添付ファイルを読み込んでいます');
      const asset=job.waiting?null:job.file?await readAttachment(job.file):photo;
      job.asset=asset;
      const managementNumbers=survey&&!asset&&!job.waiting?numberInput(job.text):undefined;
      const identifiers=survey&&!asset&&!job.waiting&&!managementNumbers?spanInputs(job.text):undefined;
      job.payload={managementNumbers,identifiers,turnProtocol:1,interactive:true,prompt:job.text,template:survey?'survey':undefined,history:projectHistory(history.slice(-8),(draft||target?.definition)?.html),previous:job.waiting?undefined:draft,...asset,...(job.waiting?{waiting:job.waiting}:{}),id:target?.id,revision:target?.revision};
    }
    step(job.payload.template==='survey'?'現調リストを準備しています':draft||target?'下書きを更新しています':'下書きを作っています');
    checkpoint({text:job.text,payload:job.payload,asset:job.asset});
    const resized=!job.file&&(resizeReference(job.text,draft||target?.definition)||targetedEdit(job.text,draft||target?.definition));
    let reply=resized||!job.file && literalEdit(job.text,draft||target?.definition);
    if(reply)step('指定された文言を変更しています');
    else reply=basicCounter(job.payload);
    if(reply&&!reply.kind)step('カウンターを組み立てています');
    if(!reply)reply=await call('sandboxDraft',job.payload,step);
    if(['advice','clarify'].includes(reply.kind)){
      const msg=bubble('assistant',reply.message), choices=reply.choices||[];
      const group=document.createElement('div');group.className='suggestions';
      for(const [index,value] of choices.entries()){
        const button=document.createElement('button');button.textContent=(index+1)+'．'+value;button.onclick=()=>send(value);group.append(button);
      }
      if(choices.length)msg.append(group);
      history.push({role:'user',text:job.text},{role:'assistant',text:reply.message,choices});
      photo=job.asset;pendingDraft=null;clearRecovery();checkpoint();return true;
    }
    const separate=reply.kind==='newDraft';
    const newPage=separate||(!draft&&!target);
    if(reply.draft?.html){
      step('下書きをブラウザで開いています');
      if(reply.steps?.length)step('下書きで操作と結果を検査しています');
      let required=reply.steps||[];
      const previousPhoto=separate?null:(draft||target?.definition)?.photo;
      let checkedPhoto=reply.draft.photo||previousPhoto;
      let error=await checkStartup(reply.draft.html,required,newPage,checkedPhoto);
      if(error){
        step('起動エラーを修正しています');
        reply=await call('sandboxDraft',{...job.payload,previous:reply.draft,repairSteps:required,prompt:'元の依頼と検査対象のidを保ち、指定の検査手順がそのまま通るように直して。 '+error+' 元の依頼：'+job.text.slice(0,1200)},step);
        checkedPhoto=reply.draft?.photo||checkedPhoto;
        const repaired=reply.steps?.length?reply.steps:required;
        let remaining=reply.draft?.html?await checkStartup(reply.draft.html,repaired,newPage,checkedPhoto):'下書きがありません';
        if(!remaining&&required.length&&JSON.stringify(required)!==JSON.stringify(repaired))remaining=await checkStartup(reply.draft.html,required,false,checkedPhoto);
        required=repaired;
        if(remaining)throw Error('修正後も検査に通りませんでした。'+remaining);
      }
      if(checkedPhoto&&usesAttachedPhoto(reply.draft.html))reply.draft.photo=checkedPhoto;
      reply.draft.html=await preserveBehavior(separate?null:(draft||target?.definition)?.html,reply.draft.html,required,undefined,checkedPhoto);
      reply.message=[reply.message,checkLabel(required)].filter(Boolean).join('。');
    }
    step('受け取った回答を確認しています');
    if(reply?.survey?.source==='db-survey-wait' && Array.isArray(reply.survey.rows) && reply.survey.rows.length===0 && !reply.survey.held?.length){
      card?.remove();card=null;draft=null;renderInfo={};photo=null;pendingDraft=null;clearRecovery();
      const message=reply.message||'該当する現調待ち案件は0件でした。冠称を確認するか、径間名や紙の写真を送ってください。';
      history.push({role:'user',text:job.text},{role:'assistant',text:message});bubble('assistant',message);checkpoint();return true;
    }
    if(typeof reply?.question==='string'&&reply.question.trim()){
      history.push({role:'user',text:job.text},{role:'assistant',text:reply.question});
      photo=job.asset;bubble('assistant',reply.question);
    }else{
      if(!resized&&job.payload.template==='survey'&&(!reply?.survey||typeof reply.survey.title!=='string'))throw Error('現調リストの下書きを受け取れませんでした。');
      const candidate=!resized&&job.payload.template==='survey'?surveyTemplate(reply.survey):reply?.draft;
      if(!candidate?.title||typeof candidate.html!=='string'||!candidate.html.trim())throw Error('下書きの内容を確認できませんでした。');
      if(!candidate.photo&&!separate&&usesAttachedPhoto(candidate.html)){
        const previousPhoto=(draft||target?.definition)?.photo;
        if(previousPhoto)candidate.photo=previousPhoto;
      }
      step('下書きのプレビューを組み立てています');
      if(separate)fresh();
      previousVersion=draft&&card?{draft,card,history:history.slice(),photo,info:renderInfo}:null;
      renderCandidate(candidate,reply,job.text);
      const choices=[...card.querySelectorAll('.suggestions button')].map(b=>b.textContent);
      history.push({role:'user',text:job.text},{role:'assistant',text:[candidate.title+' の下書き',reply.message].filter(Boolean).join('。'),choices});photo=job.asset;
    }
    pendingDraft=null;clearRecovery();checkpoint();return true;
  }catch(e){
    pendingDraft=job;
    const msg=bubble('assistant',(e.message==='Failed to fetch'?'通信が途中で切れました。':e.message)+' 入力と添付は残っています。');
    recovery(msg,'同じ内容でもう一度試す','draftRetry');return false;
  }
}
async function send(text,fromComposer=false){
  if(busy)return;
  const selected=captured||file.files[0];if(!text.trim()&&!selected)return;
  const initialField=field.value,hadText=Boolean(text.trim());
  if(fromComposer)field.value='';
  let failed=false,consumeFile=true;busy=true;newChat.disabled=true;form.querySelector('button:not([type=button])').disabled=true;
  try{
    await selectCheckpoint();
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
    const last=history.at(-1);
    const choices=last?.role==='assistant'?(last.choices||numberedChoices(last.text)):[];
    const selection=!selected&&resolveChoice(text,choices);
    if(selection?.question){bubble('assistant',selection.question);history.push({role:'user',text},{role:'assistant',text:selection.question,choices});checkpoint();return;}
    if(!selected&&/^(?:一つ前に戻して|前の版に戻して|さっきの方が(?:ええ|いい))[。！! ]*$/.test(text)){
      if(previousVersion){busy=false;card.querySelector('[data-undo]').click();busy=true;}else bubble('assistant','この会話で戻せる前の版はありません。');return;
    }
    if(!selected&&/^(?:現場の)?進入(?:路|口)(?:写真)?を登録(?:したい|する|して)?[。！! ]*$/.test(text)){entranceGuide();return;}
    if(!selected&&/^(?:これで)?(?:掲載|公開|反映|保存)(?:して|する|お願い)?[。！! ]*$/.test(text)){
      if(pendingDraft){bubble('assistant','直前の下書きがまだできていません。「同じ内容でもう一度試す」で確認してください。');return;}
      await publish();return;
    }
    if(/^(新しい会話|会話をリセット)$/.test(text)){fresh();greet();return;}
    const createRequest=/作って|作りたい|作成|作る|つくって/.test(text);
    if(!selected&&!createRequest&&/(?:を編集|を修正)(?:して|したい|する)[。！! ]*$/.test(text)&&!draft){
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
    if(survey&&createRequest&&/ゲーム/.test(text)&&!/現調|径間/.test(text))survey=false;
    const requested=surveyRequest(text);
    if(requested!==null&&!target){
      if(!selected&&!requested){beginSurvey(false);return;}
      survey=true;text=requested||'この資料から径間を取り込んで';
    }
    const explicitAll=!selected&&allWaiting.test(text);
    const soloPhoto=!hadText&&selected?.type.startsWith('image/')&&!draft&&!history.length;
    survey=survey||explicitAll||(!target&&(/現調(?:用)?リスト.{0,8}(?:作|つく)|径間.{0,5}リスト.{0,5}作/.test(text)||soloPhoto));
    pendingDraft=null;clearRecovery();
    const waiting=survey&&!selected&&!selection&&(explicitAll||(!draft&&!target&&!photo))?requestedWaiting(text):undefined;
    failed=!await generate({text:selection?.value||text,file:selected||null,waiting});
  }catch(e){failed=true;const msg=bubble('assistant',e.message==='Failed to fetch'?'通信できませんでした。時間をおいてもう一度試してください。':e.message);
    if(pendingPublication)recovery(msg,'掲載結果を確認','publishCheck');
  }
  finally{if(failed&&fromComposer&&!field.value)field.value=initialField;activity=null;work.clear();if(!failed){
    if(consumeFile&&(captured||file.files[0])===selected){file.value='';captured=null;attachment.textContent='';}
  }busy=false;newChat.disabled=false;form.querySelector('button:not([type=button])').disabled=false;log.scrollTop=log.scrollHeight;}
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

function beginSurvey(showRequest=true){
  if(field.value.trim()||captured||file.files.length){fresh();survey=true;send(field.value.trim(),true);return;}
  fresh();survey=true;
  const name=account()?.name?.trim();
  const request='現調リストを作る',question=(name?name+'さんの':'')+'現調リストを作ります。径間名か管理番号を送ってください。まとめて入力でき、紙の写真やPDFも使えます。現調待ちから選ぶときは冠称か「現調待ち全部」を送ってください。';
  history.push({role:'user',text:request},{role:'assistant',text:question});
  if(showRequest)bubble('user',request);
  bubble('assistant',question);field.focus();checkpoint();
}

root.querySelector('#survey-shortcut').onclick=()=>{if(!busy)beginSurvey();};
const newChat=root.querySelector('#sandbox-new-chat');
newChat.onclick=async()=>{
  if(busy)return;
  if(pendingPublication){
    status.textContent='掲載結果を確認してから、新しい会話を始めてください。';
    return;
  }
  if((draft||pendingDraft||captured||file.files.length||field.value.trim()) &&
     !window.confirm('編集中の下書き・入力・添付を閉じて、新しい会話を始めますか？'))return;
  busy=true;
  try{
    await selectCheckpoint();
    fresh();
    form.reset();captured=null;attachment.textContent='';
    activity=null;renderInfo={};work.clear();status.textContent='';
    log.replaceChildren();
    if(createSurvey)window.history.replaceState({...window.history.state,sandboxBlank:true,surveyEntry:true},'');
    greet();field.focus();
  }finally{busy=false;}
};
async function restore(){
  await selectCheckpoint();
  if(checkpointKey){
    let saved;
    try{saved=unpackCheckpoint(checkpointStore.getItem(checkpointKey));}catch{}
    if(createSurvey && !saved && window.history.state?.sandboxBlank){log.replaceChildren();greet();return;}
    if(createSurvey && (!window.history.state?.surveyEntry || !saved)){
      window.history.replaceState({...window.history.state,surveyEntry:true},'');
      const request=sessionStorage.getItem('ippatsu.survey.createPrompt');
      sessionStorage.removeItem('ippatsu.survey.createPrompt');
      log.replaceChildren();beginSurvey();
      const input=request && surveyRequest(request);
      if(input)await send(input);
      return;
    }
    if(saved){
      history=saved.history||[];target=saved.target;survey=saved.survey;photo=saved.photo;
      for(const turn of history)bubble(turn.role,turn.text+(turn.choices?.length?'\n'+turn.choices.map((v,i)=>(i+1)+'．'+v).join('\n'):''));
      if(saved.previous){
        const old=saved.previous;
        renderCandidate(old.draft,old.info?.reply||{},old.info?.request||'');
        previousVersion={...old,card};
      }
      if(saved.draft)renderCandidate(saved.draft,saved.renderInfo?.reply||{},saved.renderInfo?.request||'');
      if(saved.pendingPublication){pendingPublication=saved.pendingPublication;recovery(bubble('assistant','前回の掲載結果を照合できます。'),'掲載結果を確認','publishCheck');}
      else if(saved.job){pendingDraft=saved.job;recovery(bubble('assistant','前回の生成結果を受け取る前に画面が閉じられました。'),'同じ依頼で再開','draftRetry');}
    }
  }
}
await restore();
window.addEventListener("survey-unlocked",restore);
