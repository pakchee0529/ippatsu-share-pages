import {account, accountButton, openAccount} from '../../account/session.mjs';
import {addOverlay, compressPhoto, photoEditor} from './photo.mjs';

const endpoint = 'https://evmgsqdrojxppxknrzfk.supabase.co/functions/v1/field-entrance';
const el = id => document.getElementById(id);
const dateFormat = new Intl.DateTimeFormat('ja-JP',{timeZone:'Asia/Tokyo',year:'numeric',month:'numeric',day:'numeric'});
const text = (tag,value) => {const node=document.createElement(tag);node.textContent=value;return node;};
let current, searchVersion=0, photoVersion=0, fileVersion=0, uploading=false;
const params=new URLSearchParams(location.search);
const registerMode=params.get('mode')==='register';
let trial=false, casesLoaded=false;
accountButton(el('account-entry'));

async function request(body) {
  const multipart = body instanceof FormData;
  const headers = multipart ? {} : {'Content-Type':'application/json'};
  if (multipart && account()) headers['x-ippatsu-session'] = account().token;
  const response = await fetch(endpoint,{method:'POST',headers,body:multipart?body:JSON.stringify(body)});
  const data = await response.json().catch(()=>({}));
  if (!response.ok) {
    const fallback = response.status===401 ? 'ログインの期限が切れました。ログインしてから再度保存してください。'
        : response.status===409 ? '現場の状態が変わりました。現場を選び直してください。'
        : '通信できませんでした。もう一度お試しください。';
    const error=Error(data.message || fallback); error.status=response.status; throw error;
  }
  return data;
}

function meta(item) {
  return [item.design_number ? '設計番号 '+item.design_number : '設計番号 未登録', item.management_no && '管理番号 '+item.management_no, item.episode_no && '受付'+item.episode_no+'回目'].filter(Boolean).join('　');
}
async function listCases(target) {
  const version=++searchVersion;
  casesLoaded=true;
  const q=el('query').value.trim();
  el('search-status').textContent='現場を探しています…';
  el('cases').replaceChildren();
  try {
    const {cases}=await request({action:'cases',q});
    if(version!==searchVersion) return;
    const found=cases.find(item=>item.id===target);
    if (found) {openCase(found);return;}
    el('search-status').textContent=target?'この受付は現在の一覧にありません。':cases.length?'':'該当する現場がありません。';
    for (const item of cases) {
      const li=document.createElement('li'), btn=document.createElement('button');
      btn.type='button';btn.append(text('strong',item.label),text('small',meta(item)));
      btn.onclick=()=>openCase(item); li.append(btn); el('cases').append(li);
    }
  } catch(e) {if(version===searchVersion)el('search-status').textContent=e.message;}
}
el('search').onsubmit=e=>{e.preventDefault();listCases();};

function figure(photo, large=false) {
  const fig=document.createElement('figure');
  const frame=document.createElement(large?'div':'button');
  frame.className='photo';
  if (!large) {
    frame.type='button'; frame.setAttribute('aria-label','進入口の写真を拡大');
    frame.onclick=()=>{el('large-photo').replaceChildren(figure(photo,true));el('viewer').showModal();};
  }
  const img=new Image(); img.alt=photo.note||'現場の進入口'; img.loading=large?'eager':'lazy';
  frame.append(img);addOverlay(frame,img,photo.arrows || []);img.src=photo.url;
  img.onerror=()=>{if(!photo.url.startsWith('blob:')){el('photos-status').textContent='写真を読み込めません。再読み込みで写真を取得し直せます。';el('retry').hidden=false;}};
  const caption=text('figcaption','');
  if(photo.route_count>1)caption.append(text('strong','道順 '+photo.route_index+' / '+photo.route_count),document.createElement('br'));
  caption.append(document.createTextNode(photo.note||''));
  const date=new Date(photo.created_at);
  caption.append(text('small',[photo.episode_no && '受付'+photo.episode_no+'回目',Number.isFinite(+date)&&dateFormat.format(date),photo.author].filter(Boolean).join('　')));
  fig.append(frame,caption);return fig;
}
el('close-viewer').onclick=()=>el('viewer').close();
async function listPhotos() {
  if(!current)return;
  const version=++photoVersion;
  el('photos-status').textContent='写真を読み込んでいます…'; el('retry').hidden=true;
  el('photos').replaceChildren();
  try {
    const {photos}=await request({action:'list',case_id:current.id});
    if(version!==photoVersion)return;
    el('photos-status').textContent='';
    for(const previous of [false,true]){
      const rows=photos.filter(photo=>Boolean(photo.previous)===previous);
      if(previous&&!rows.length)continue;
      el('photos').append(text('h3',previous?'前回までの進入口':'今回の進入口'));
      if(!rows.length)el('photos').append(text('p','今回の写真はまだありません。'));
      for(const row of rows)el('photos').append(figure(row));
    }
  } catch(e){if(version===photoVersion){el('photos-status').textContent=e.message;el('retry').hidden=false;}}
}
el('retry').onclick=listPhotos;
function openCase(item) {
  current=item; el('selected-label').textContent=item.label;el('selected-meta').textContent=meta(item);
  el('picker').hidden=true;el('detail').hidden=false;el('selected-label').focus();
  listPhotos();
  if(registerMode && !el('editor').open) showEditor();
}
el('back').onclick=()=>{
  current=null;photoVersion++;el('detail').hidden=true;el('picker').hidden=false;el('query').focus();listCases();
};
const report=value=>{el('upload-status').textContent=value;};
const editor=photoEditor(el('canvas'),el('undo'),report);
let route, active, preparing=false;
const paused=new Map();
function pendingKey() {return account()?.token && current?.id ? account().token+'|'+current.id : null;}
function release() {
  for(const image of route?.items||[])URL.revokeObjectURL(image.url);
  route=active=null;editor.clear();
}
function drawOrder() {
  const items=route.items, index=items.indexOf(active);
  const blocked=preparing||route.started;
  el('order').hidden=!items.length;
  el('sequence').replaceChildren();
  for(const [i,item] of items.entries()){
    const btn=text('button','');btn.type='button';btn.dataset.index=i;
    const thumb=new Image();thumb.alt='';thumb.src=item.url;
    btn.append(thumb,text('span',(i+1)+'枚目'));
    btn.setAttribute('aria-pressed',String(item===active));
    btn.disabled=blocked;btn.onclick=()=>activate(item);el('sequence').append(btn);
  }
  el('earlier').disabled=blocked||index<=0;el('later').disabled=blocked||index<0||index>=items.length-1;
  el('remove-photo').disabled=blocked||index<0;
  el('file').disabled=el('camera').disabled=blocked||items.length>=30;
  el('preview-button').disabled=preparing||!items.length;
  el('note').disabled=blocked||!active;el('drawing').hidden=!active;
  el('canvas').inert=blocked;
}
async function activate(item) {
  active=item;editor.clear();el('note').value=item?.note||'';drawOrder();
  if(!item)return;
  try {await editor.show(item);}
  catch{if(active===item)report('写真を表示できませんでした。写真を選び直してください。');}
}
el('note').oninput=()=>{if(active)active.note=el('note').value;};
function move(delta){
  const from=route.items.indexOf(active), to=from+delta;
  if(route.started||from<0||to<0||to>=route.items.length)return;
  route.items.splice(to,0,route.items.splice(from,1)[0]);drawOrder();
  el('sequence').children[to].scrollIntoView({block:'nearest',inline:'nearest'});
}
el('earlier').onclick=()=>move(-1);el('later').onclick=()=>move(1);
el('remove-photo').onclick=()=>{
  if(route.started||!active)return;
  const i=route.items.indexOf(active);
  URL.revokeObjectURL(active.url);route.items.splice(i,1);activate(route.items[Math.min(i,route.items.length-1)]);
};
function showEditor(tryOnly=false) {
  if(!tryOnly&&!current)return;
  trial=tryOnly;
  release();el('upload').reset();fileVersion++;preparing=false;
  route={id:crypto.randomUUID(),items:[],started:false};drawOrder();
  el('preview-button').disabled=true;el('drawing').hidden=true;report('');
  el('editor-title').textContent=trial?'写真で矢印を試す':'進入路を登録';
  el('editor-case').textContent=trial?'写真はこの端末で表示されます。保存や共有はされません。':current.label+'　'+meta(current);
  el('editor').showModal();
  const key=pendingKey();
  if(!trial&&key&&paused.has(key)){
    route=paused.get(key);paused.delete(key);el('upload').requestSubmit();
    el('preview-back').disabled=true;el('preview-pause').hidden=false;el('confirm-save').textContent='続きから保存';
  }
}
el('add').onclick=()=>showEditor();
el('try-photo').onclick=()=>showEditor(true);
el('close-editor').onclick=()=>el('editor').close();
el('editor').oncancel=e=>{if(uploading)e.preventDefault();};
el('editor').onclose=()=>{fileVersion++;release();if(!casesLoaded)listCases();};
async function selectFile(event) {
  const files=Array.from(event.target.files);
  event.target.value='';
  if(!files.length||preparing||route.started)return;
  if(route.items.length+files.length>30){report('一度に使える写真は30枚までです。枚数を減らして選び直してください。');return;}
  const version=++fileVersion,added=[],failed=[];
  preparing=true;drawOrder();
  try {
    for(const [i,file] of files.entries()){
      report('写真を準備しています（'+(i+1)+' / '+files.length+'）');
      try{
        const blob=await compressPhoto(file);
        if(version!==fileVersion)return;
        const item={id:crypto.randomUUID(),blob,url:URL.createObjectURL(blob),arrows:[],note:'',saved:false};
        route.items.push(item);added.push(item);
      }catch{if(version!==fileVersion)return;failed.push(file.name);}
    }
  }finally{
    if(version===fileVersion){
      preparing=false;await activate(added[0]||active);
      report(failed.length?'読み込めなかった写真：'+failed.join('、'):'');
    }
  }
}
el('file').onchange=selectFile;el('camera').onchange=selectFile;
el('upload').onsubmit=e=>{
  e.preventDefault();
  if(!route.items.length||preparing)return;
  el('preview-output').replaceChildren(...route.items.map((item,i)=>figure({...item,route_index:i+1,route_count:route.items.length,episode_no:trial?null:current.episode_no,author:trial?null:account()?.name},true)));
  el('preview-context').textContent=trial?'試し描きです。この写真は共有されません。':current.label+'　'+meta(current);
  el('confirm-save').textContent=route.items.length+'枚をこの現場に保存';
  el('confirm-save').hidden=trial;el('preview-finish').hidden=!trial;el('preview-pause').hidden=true;el('preview-back').disabled=false;el('preview-status').textContent='';
  el('preview-dialog').showModal();
};
el('preview-dialog').onclose=()=>{el('preview-output').replaceChildren();};
el('preview-dialog').oncancel=e=>{if(uploading||route?.started)e.preventDefault();};
el('preview-back').onclick=()=>el('preview-dialog').close();
el('preview-finish').onclick=()=>{el('preview-dialog').close();el('editor').close();};
el('preview-pause').onclick=()=>{
  if(uploading)return;
  const key=pendingKey();
  if(key){paused.set(key,route);route=null;}
  el('preview-dialog').close();el('editor').close();
  el('photos-status').textContent=key?'このタブで「進入口の写真を追加」を押すと、続きから保存できます。':'保存を中断しました。';
};
el('confirm-save').onclick=async ()=>{
  if(uploading||trial||!current)return;
  const feedback=el('preview-status');
  if(!account()){openAccount(()=>{accountButton(el('account-entry'));feedback.textContent='ログインしました。保存を押してください。';});return;}
  if(!route.items.length)return;
  const controls=[el('confirm-save'),el('preview-back')];
  controls.forEach(c=>c.disabled=true);el('preview-pause').hidden=true;uploading=true;route.started=true;
  try{
    for(const [i,item] of route.items.entries()){
      if(item.saved)continue;
      feedback.textContent=(i+1)+' / '+route.items.length+' 枚目を保存しています…';
      const form=new FormData();form.set('action','upload');form.set('case_id',current.id);form.set('id',item.id);
      form.set('route_id',route.id);form.set('route_index',String(i+1));form.set('route_count',String(route.items.length));
      form.set('image',item.blob,'entrance.jpg');form.set('arrows',JSON.stringify(item.arrows));form.set('note',item.note.trim());
      const result=await request(form);
      if(result.id!==item.id)throw Error('保存結果を確認できませんでした。');
      item.saved=true;
    }
    el('preview-dialog').close();el('editor').close();await listPhotos();
  }catch(error){
    feedback.textContent=route.items.filter(item=>item.saved).length+' / '+route.items.length+' 枚の保存を確認。'+error.message;
    el('confirm-save').textContent='続きから保存';
    el('preview-pause').hidden=false;
    if(error.status===401)openAccount(()=>{accountButton(el('account-entry'));feedback.textContent='ログインしました。「続きから保存」を押してください。';});
  }
  finally{uploading=false;el('confirm-save').disabled=false;}
};
if(registerMode){
  el('intro').textContent='現場を選んで写真に矢印を描き、仕上がりを確認して登録できます。';
  el('picker-title').textContent='登録する現場を選ぶ';
}
el('query').value=(params.get('q')||'').slice(0,100);
if(params.get('mode')==='try')showEditor(true);
else listCases(params.get('case_id'));
