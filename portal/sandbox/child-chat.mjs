import {call} from './api.mjs';
import {previewPage} from './preview.mjs';

function button(text,fn){
  const el=document.createElement('button');el.type='button';el.textContent=text;el.onclick=fn;return el;
}
function changeRows(item,survey,add,remove){
  const doc=new DOMParser().parseFromString(item.definition.html,'text/html');
  const first=doc.getElementById(survey.rows[0]?.key)?.closest('label');
  const group=first?.parentElement||doc.querySelector('[data-survey-rows]');
  if(!group)throw Error('リストの形式を確認してください。');
  group.dataset.surveyRows='';
  if(add){
    const label=document.createElement('label'),check=document.createElement('input'),name=document.createElement('span');
    label.className=first?.className||'item';name.className=first?.querySelector('span')?.className||'name';
    check.type='checkbox';check.id='visit-'+crypto.randomUUID();name.textContent=add;
    label.append(check,name);group.append(label);
  }
  for(const row of remove)doc.getElementById(row.key)?.closest('label')?.remove();
  return {title:item.definition.title,html:'<!doctype html>'+doc.documentElement.outerHTML};
}
export function childChat(item,survey){
  const el=id=>document.getElementById(id);
  const dialog=el('child-chat'),launch=el('chat-launch'),log=el('child-log'),actions=el('child-actions'),form=el('child-form'),input=el('child-input');
  el('chat-context').textContent=item.definition.title;launch.hidden=false;
  launch.onclick=()=>dialog.showModal();el('chat-close').onclick=()=>dialog.close();
  let draft=null,awaitingName=false,editing=false,busy=false;
  const history=[];
  function say(text,mine=false){
    const p=document.createElement('p');p.textContent=text;p.className=mine?'mine':'reply';log.append(p);log.scrollTop=log.scrollHeight;
    history.push({role:mine?'user':'assistant',text});return p;
  }
  function quick(){actions.replaceChildren();
    for(const text of [...(survey?['次どこ？','径間を追加','チェック済みを削除','巡回順を提案']:[]),'ページを編集']){
      actions.append(button(text,()=>{editing=false;awaitingName=false;send(text);}));
    }
  }
  function confirmation(text,apply){
    say(text);actions.replaceChildren(button('反映する',async()=>{
      if(busy)return;busy=true;
      try{await apply();}catch(e){say(e.message);quick();}finally{busy=false;}
    }),button('やめる',()=>{draft=null;editing=false;awaitingName=false;say('変更を取り消しました。');quick();}));
  }
  async function save(d){
    const result=await call('sandboxPublish',{id:item.id,revision:item.revision,draft:d});
    if(result.id!==item.id||result.revision!==item.revision+1)throw Error('保存結果を確認してください。');
    location.reload();
  }
  async function send(raw){
    if(busy)return;const text=raw.trim();if(!text)return;
    input.value='';say(text,true);quick();busy=true;form.querySelector('button').disabled=true;
    try{
      if(!editing&&survey&&/次.*(どこ|何処|現場|径間)|次は[？?]?$/.test(text)){
        awaitingName=false;await survey.ready;const r=survey.next();
        const p=say(r?'次は「'+r.name+'」です。'+(r.corrected?'電柱名に補正候補があります。':''):'未訪問の径間はありません。');
        if(r?.url){const a=document.createElement('a');a.href=r.url;a.target='_blank';a.rel='noopener noreferrer';a.textContent='2点地図を開く';p.append(document.createElement('br'),a);}
        else if(r)say('両端の座標を確認できていません。');return;
      }
      if(!editing&&survey&&/チェック済|訪問済/.test(text)&&/削除|消し|消す|除い/.test(text)){
        awaitingName=false;const remove=survey.checked();if(!remove.length){say('チェック済みの径間はありません。');return;}
        confirmation('共有リストから次の'+remove.length+'件を削除します。\n'+remove.map(r=>r.name).join('\n'),()=>save(changeRows(item,survey,null,remove)));return;
      }
      if(!editing&&survey&&(awaitingName||/追加/.test(text)&&/径間|[～〜~]/.test(text))){
        const name=text.normalize('NFKC').match(/[^\s「」、。]+?\d[A-Za-z\d]*[~〜][^\s「」、。]*?\d[A-Za-z\d]*/)?.[0]?.replace(/^.*?(?:追加して|追加[:：]|径間[:：])/,'').replace(/^[「『]/,'');
        if(!name){awaitingName=true;say('追加する径間名を入力してください。');return;}
        awaitingName=false;
        if(survey.rows.some(r=>r.name.normalize('NFKC').replace(/〜/g,'~')===name.replace(/〜/g,'~'))){say('その径間は登録済みです。');return;}
        confirmation('共有リストに「'+name+'」を追加します。',()=>save(changeRows(item,survey,name,[])));return;
      }
      if(!editing&&survey&&/巡回順|近い順|遠い順/.test(text)){
        await survey.ready;const near=text.includes('近い順'),route=survey.route(near);if(!route.some(r=>r.center)){say('座標を照合できませんでした。');return;}
        confirmation((near?'会社のある上之町から近い順です。':'遠い現場から回る巡回案です。')+'\n'+route.map((r,i)=>(i+1)+'　'+r.name).join('\n'),()=>{survey.applyRoute(route);say('この端末の訪問順に反映しました。');quick();});return;
      }
      if(text==='ページを編集'){editing=true;awaitingName=false;say('このページのどこをどう変えたいですか？');return;}
      const reply=await call('sandboxDraft',{id:item.id,revision:item.revision,prompt:text,interactive:true,history:history.slice(-9,-1),previous:draft});
      if(reply.question){say(reply.question);return;}
      draft=reply.draft;log.append(previewPage(draft.html));confirmation('修正版の下書きです。共有ページに反映しますか？',()=>save(draft));
    }catch(e){say(e.message);}finally{busy=false;form.querySelector('button').disabled=false;log.scrollTop=log.scrollHeight;}
  }
  form.onsubmit=e=>{e.preventDefault();send(input.value);};quick();
}

