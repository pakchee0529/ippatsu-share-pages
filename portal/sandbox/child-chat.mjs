import {nearbyIntent,nearbyChoice,listCase} from './child-near.mjs';
import {addition,surveyFile} from './child-add.mjs?v=crown-request2';
import {surveyTemplate,compactSurveyId} from '../assistant/survey-template.mjs?v=childwaiting1';
import {resizeReference} from './reference.mjs?v=size1';
import {resolveChoice} from '../assistant/choices.mjs?v=short1';
import {literalEdit,targetedEdit} from '../assistant/short-edits.mjs?v=local2';
import {preserveBehavior,projectHistory} from '../assistant/behavior-history.mjs?v=mobile4';
import {checkStartup,checkLabel} from '../assistant/sandbox-check.mjs?v=mobile4';
import {appearance,requestedAppearance,stamp} from './appearance.mjs';
import {call} from './api.mjs';
import {previewPage} from './preview.mjs';

function button(text,fn){
  const el=document.createElement('button');el.type='button';el.textContent=text;el.onclick=fn;return el;
}
function changeRows(item,survey,add,remove){
  const doc=new DOMParser().parseFromString(item.definition.html,'text/html');
  const first=doc.getElementById(survey.rows[0]?.key)?.closest('label');
  const group=doc.querySelector('[data-survey-rows]')||first?.parentElement;
  if(!group)throw Error('リストの形式を確認してください。');
  group.dataset.surveyRows='';
  if(add){
    const label=document.createElement('label'),check=document.createElement('input'),name=document.createElement('span');
    label.className=first?.className||'item';name.className=first?.querySelector('span')?.className||'name';
    check.type='checkbox';check.id='visit-'+crypto.randomUUID();name.textContent=add;
    label.append(check,name);group.append(label);
  }
  for(const row of remove){const label=doc.getElementById(row.key)?.closest('label');if((label?.dataset.referenceNumber||label?.dataset.review)&&label.parentElement.parentElement===group)label.parentElement.remove();else label?.remove();}
  return {title:item.definition.title,html:'<!doctype html>'+doc.documentElement.outerHTML};
}
const spanIdentity=name=>name.normalize('NFKC').replace(/[〜～]/g,'~').replace(/\s/g,'');
const caseNumber=text=>String(text||'').normalize('NFKC').match(/(?:^|管理番号\s*)(\d{8})(?=\s*(?:[／/]|$))/)?.[1];
function appendWaiting(item,survey,found){
  const doc=new DOMParser().parseFromString(item.definition.html,'text/html');
  const first=doc.getElementById(survey.rows[0]?.key)?.closest('label');
  const group=doc.querySelector('[data-survey-rows]')||first?.parentElement;
  if(!group)throw Error('リストの形式を確認してください。');
  const add=[],held=(found.held||[]).map(row=>[row.number,row.name,row.message].filter(Boolean).join(' ')||'原票行');
  const ids=new Set(survey.rows.map(r=>r.key));
  let skipped=found.duplicates?.length||0;
  for(const row of found.rows){
    if(found.manualNames?.has(spanIdentity(row.name||'')) && !row.case_id && !row.management_no && row.name){
      if([...survey.rows,...add].some(r=>spanIdentity(r.name)===spanIdentity(row.name)))skipped++;
      else add.push(row);
      continue;
    }
    if(typeof row.name!=='string'||!/[〜～~]/.test(row.name)||!/^[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}$/i.test(row.case_id)){
      held.push([row.management_no,row.name,row.review||'案件未確定'].filter(Boolean).join(' '));continue;
    }
    const full='span-case-'+row.case_id.toLowerCase(),short=compactSurveyId(row.case_id);
    if(ids.has(full)||ids.has(short)){skipped++;continue;}
    // A manually entered row may lack a case UUID. Keep both its check and its position intact.
    if(survey.rows.some(r=>{
      if(r.key.startsWith('span-case-')||r.key.startsWith('c-'))return false;
      const number=caseNumber(r.reference);
      return number ? number===row.management_no : spanIdentity(r.name)===spanIdentity(row.name);
    })){
      held.push(row.management_no+' '+row.name);continue;
    }
    ids.add(full);ids.add(short);add.push(row);
  }
  if(add.length){
    group.dataset.surveyRows='';
    const source=group.hasAttribute('data-waiting-list')?'db-survey-wait':undefined;
    const generated=surveyTemplate({title:item.definition.title,rows:add,source});
    const block=new DOMParser().parseFromString(generated.html,'text/html').querySelector('[data-survey-rows]');
    const before=group.querySelector(':scope > [data-survey-notices]');
    for(const node of [...block.children])group.insertBefore(doc.importNode(node,true),before);
  }
  return {add,held,skipped,definition:{title:item.definition.title,html:'<!doctype html>'+doc.documentElement.outerHTML}};
}
export function childChat(item,survey){
  const el=id=>document.getElementById(id);
  const dialog=el('child-chat'),launch=el('chat-launch'),log=el('child-log'),actions=el('child-actions'),form=el('child-form'),input=el('child-input');
  const fileInput=el('child-file');
  el('child-file-label').hidden=!survey;
  el('chat-context').textContent=item.definition.title;launch.hidden=false;
  launch.onclick=()=>dialog.showModal();el('chat-close').onclick=()=>dialog.close();
  let draft=null,awaitingName=false,editing=false,busy=false;
  const history=[];
  let lastChoices=[],nearbyRows=[];
  const rollbackKey='ippatsu.sandbox.rollback.'+item.id;
  function rollback(){
    try{const old=JSON.parse(sessionStorage.getItem(rollbackKey));return old?.revision===item.revision?old:null;}catch{return null;}
  }
  function restore(){
    const old=rollback();
    if(!old){say('この端末で戻せる版はありません。');return;}
    confirmation('ページの作りを一つ前に戻しますか？ 保存された入力値は保持します。',()=>save(old.definition));
  }
  function say(text,mine=false){
    const p=document.createElement('p');p.textContent=text;p.className=mine?'mine':'reply';log.append(p);log.scrollTop=log.scrollHeight;
    history.push({role:mine?'user':'assistant',text});return p;
  }
  function quick(){actions.replaceChildren();
    if(rollback())actions.append(button('前の版に戻す',restore));
    if(draft)actions.append(button('今の下書きを反映',()=>confirmation('この下書きを共有ページに保存しますか？',()=>save(draft))));
    for(const text of [...(survey?['次どこ？','径間を追加','チェック済みを削除','おすすめの訪問順を見る']:[]),'ページを編集']){
      actions.append(button(text,()=>{editing=false;awaitingName=false;send(text);}));
    }
  }
  function confirmation(text,apply){
    say(text);actions.replaceChildren(button('反映する',async()=>{
      if(busy)return;busy=true;
      try{await apply();}catch(e){say(e.message);quick();}finally{busy=false;}
    }),button('やめる',()=>{draft=null;editing=false;awaitingName=false;say('変更を取り消しました。');quick();}));
  }
  async function save(d,appearance){
    const result=await call('sandboxPublish',{id:item.id,revision:item.revision,draft:d,appearance});
    if(result.id!==item.id||result.revision!==item.revision+1)throw Error('保存結果を確認してください。');
    try{sessionStorage.setItem(rollbackKey,JSON.stringify({revision:result.revision,definition:item.definition}));}catch{}
    location.reload();
  }
  async function send(raw){
    if(busy)return;const file=survey&&fileInput.files[0];let text=raw.trim()||(file?'この資料の径間を追加':'');if(!text)return;
    const choice=resolveChoice(text,lastChoices);
    if(choice?.question){say(choice.question);return;}
    text=choice?.value||text;lastChoices=[];
    input.value='';say(text,true);quick();busy=true;form.querySelector('button').disabled=true;
    try{
      if(/^(一つ前に戻して|前の版に戻して|さっきの方が(?:ええ|いい))[。！! ]*$/.test(text)){restore();return;}
      const look=/一覧.{0,6}(?:目印|アイコン|色)|(?:ページ|砂場)のアイコン|^(?:アイコン|マーク)(?:を|は)/.test(text)&&requestedAppearance(text,item.definition);
      if(look){confirmation('一覧の目印を「'+look.label+'」にしますか？',()=>save(item.definition,look.style));return;}
      const editInterface=/ボタン|見出し|レイアウト|フォント|ラベル|文字色|背景色|機能を|仕組みを/.test(text);
      const surveyCommand=!editing&&survey&&!editInterface;
      const pick=surveyCommand&&!file&&nearbyRows.length?nearbyChoice(text):null;
      const picked=pick?nearbyRows[pick-1]:null;
      if(pick&&!picked){say('表示した候補の番号を選んでください。');return;}
      nearbyRows=[];
      if(surveyCommand&&!file&&nearbyIntent(text)){
        awaitingName=false;await survey.ready;
        const origin=/現在地|今いる|今の位置/.test(text)?await survey.currentOrigin():
          /起点を選|起点を変/.test(text)?await survey.chooseOrigin():survey.lastCheckedOrigin()||await survey.chooseOrigin();
        if(!origin){say('起点の選択を取り消しました。');return;}
        const reply=await call('sandboxDraft',{turnProtocol:1,interactive:true,template:'survey',prompt:text,
          nearbySurvey:{origin:{name:origin.name,point:origin.point},existing:survey.rows.map(listCase)}});
        if(reply.survey?.source!=='nearby-survey-wait'||!Array.isArray(reply.survey.rows))throw Error('近くの現調待ちを照合できませんでした。');
        nearbyRows=reply.survey.rows.slice(0,3).filter(r=>Number.isFinite(r.distance_km)&&r.distance_km>=0&&r.case_id);
        if(!nearbyRows.length){say(reply.survey.message||'位置を確認できた未登録の現調待ちはありません。');return;}
        const omitted=reply.survey.unlocated?'\n座標を確認できない'+reply.survey.unlocated+'件は除いています。':'';
        say(origin.name+'から近い現調待ちです（直線距離）。\n'+nearbyRows.map((r,i)=>(i+1)+'．'+r.name+'　'+r.management_no+'　'+r.distance_km.toFixed(2)+' km').join('\n')+omitted+'\n追加する番号を選んでください。');
        actions.replaceChildren(...nearbyRows.map((r,i)=>button((i+1)+'番　'+r.name,()=>send((i+1)+'番で'))),
          button('起点を変える',()=>send('起点を変えて近くの候補を探して')));return;
      }
      if(surveyCommand&&/次.*(どこ|何処|現場|径間)|次は[？?]?$/.test(text)){
        awaitingName=false;await survey.ready;const r=survey.next();
        const p=say(r?'次は「'+r.name+'」です。'+(r.corrected?'この電柱で合っていますか？ 地図で確認してください。':''):'未訪問の径間はありません。');
        if(r?.url){const a=document.createElement('a');a.href=r.url;a.target='_blank';a.rel='noopener noreferrer';a.textContent='両端の電柱を見る';p.append(document.createElement('br'),a);}
        else if(r)say('両端の座標を確認できていません。');return;
      }
      if(surveyCommand&&/チェック済|訪問済/.test(text)&&/削除|消し|消す|除い/.test(text)){
        awaitingName=false;const remove=survey.checked();if(!remove.length){say('チェック済みの径間はありません。');return;}
        confirmation('共有リストから次の'+remove.length+'件を削除します。\n'+remove.map(r=>r.name).join('\n'),()=>save(changeRows(item,survey,null,remove)));return;
      }
      const selection=surveyCommand&&addition(text,awaitingName);
      if(survey&&(picked||file||selection||surveyCommand&&(awaitingName||/径間を追加/.test(text)))){
        if(!picked&&!file&&!selection){awaitingName=true;say('径間名・管理番号・冠称を入力するか、紙の写真やPDFを選んでください。複数の径間名や番号は改行で指定できます。');return;}
        let found,scope;
        const params=picked?{}:file?{...await surveyFile(file),surveyTitle:item.definition.title}:selection;
        const reply=picked?{survey:{rows:[picked]}}:await call('sandboxDraft',{turnProtocol:1,interactive:true,template:'survey',prompt:text,...params});
        found=reply.survey;
        if(!Array.isArray(found?.rows)||params.waiting&&found.source!=='db-survey-wait')throw Error(reply.question||reply.message||'追加する案件を照合できませんでした。');
        if(params.identifiers)found.manualNames=new Set(params.identifiers.map(spanIdentity));
        scope=picked?'選んだ候補':file?file.name:params.waiting?(params.waiting.scope==='all'?'現調待ち全件':params.waiting.crown+'の現調待ち'):params.identifiers?'指定の径間・管理番号':'指定の管理番号';
        const {add,skipped,held,definition}=appendWaiting(item,survey,found);
        const summary=scope+'：追加 '+add.length+'件、登録済み・重複 '+skipped+'件、要確認 '+held.length+'件。';
        const notes=[held.length?'照合を保留：'+held.join('、'):'',found.auditNotice].filter(Boolean).map(s=>'\n'+s).join('');
        fileInput.value='';
        if(!add.length){say(summary+notes);return;}
        const stored=stamp(definition,appearance(item.definition));
        const size=JSON.stringify({action:'sandboxPublish',id:item.id,revision:item.revision,draft:stored,device:'0'.repeat(64)}).length;
        if(stored.html.length>25000||size>32000){say(summary+'\nまとめて追加するとこのリストの保存上限を超えます。別の現調リストを作るか、径間名を指定して追加してください。');return;}
        awaitingName=false;
        confirmation(summary+'\n「'+item.definition.title+'」の末尾に追加します。\n'+add.map(row=>[row.management_no,row.name,row.review].filter(Boolean).join('　')).join('\n')+notes,()=>save(definition));return;
      }
      if(surveyCommand&&/訪問順|巡回順|近い順|遠い順/.test(text)){
        await survey.ready;const near=text.includes('近い順'),origin=await survey.chooseOrigin();if(!origin)return;const route=survey.route(near,origin.point);if(!route.some(r=>r.center)){say('座標を照合できませんでした。');return;}
        confirmation((origin.name+'から'+(near?'近い現場':'遠い現場')+'から回る巡回案です。')+'\n'+route.map((r,i)=>(i+1)+'　'+r.name).join('\n'),()=>{survey.applyRoute(route);say('この端末の訪問順に反映しました。');quick();});return;
      }
      if(text==='ページを編集'){editing=true;awaitingName=false;say('このページのどこをどう変えたいですか？');return;}
      const request={turnProtocol:1,id:item.id,revision:item.revision,prompt:text,interactive:true,history:projectHistory(history.slice(-9,-1),(draft||item.definition).html),previous:draft};
      let reply=resizeReference(text,draft||item.definition)||targetedEdit(text,draft||item.definition)||literalEdit(text,draft||item.definition)||await call('sandboxDraft',request);
      if(['advice','clarify'].includes(reply.kind)){
        const options=reply.choices||[];lastChoices=options;
        say(reply.message+(options.length?'\n'+options.map((v,i)=>(i+1)+'．'+v).join('\n'):''));
        for(const option of options)actions.append(button(option,()=>send(option)));
        return;
      }
      if(reply.question){say(reply.question);return;}
      const checks=reply.steps||[];
      const failure=await checkStartup(reply.draft.html,checks);
      if(failure){
        reply=await call('sandboxDraft',{...request,previous:reply.draft,repairSteps:checks,prompt:'検査対象のidと仕様を維持して、この動作エラーを直して：'+failure+'。元の依頼：'+text.slice(0,1200)});
        if(!reply.draft||await checkStartup(reply.draft.html,checks))throw Error('修正後も操作を確認できませんでした。');
      }
      reply.draft.html=await preserveBehavior((draft||item.definition).html,reply.draft.html,checks);
      draft=reply.draft;log.append(previewPage(draft.html));confirmation(checkLabel(checks)+'。共有ページに保存しますか？',()=>save(draft));
    }catch(e){say(e.message);}finally{busy=false;form.querySelector('button').disabled=false;log.scrollTop=log.scrollHeight;}
  }
  form.onsubmit=e=>{e.preventDefault();send(input.value);};quick();
}

