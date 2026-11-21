import {account, accountButton, openAccount} from '../../account/session.mjs';
import {addOverlay, photoEditor} from './photo.mjs';

const endpoint = 'https://evmgsqdrojxppxknrzfk.supabase.co/functions/v1/field-entrance';
const el = id => document.getElementById(id);
const dateFormat = new Intl.DateTimeFormat('ja-JP',{timeZone:'Asia/Tokyo',year:'numeric',month:'numeric',day:'numeric'});
const text = (tag,value) => {const node=document.createElement(tag);node.textContent=value;return node;};
let current, searchVersion=0, photoVersion=0, fileVersion=0, uploading=false, submissionId;
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
  return [item.management_no && '管理番号 '+item.management_no, item.episode_no && '受付'+item.episode_no+'回目'].filter(Boolean).join('　');
}
async function listCases(target) {
  const version=++searchVersion;
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
  img.onerror=()=>{el('photos-status').textContent='写真を読み込めません。再読み込みで写真を取得し直せます。';el('retry').hidden=false;};
  const caption=text('figcaption',photo.note||'');
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
}
el('back').onclick=()=>{
  current=null;photoVersion++;el('detail').hidden=true;el('picker').hidden=false;el('query').focus();listCases();
};
const report=value=>{el('upload-status').textContent=value;};
const editor=photoEditor(el('canvas'),el('undo'),report);
function showEditor() {
  if(!current)return;
  el('upload').reset();editor.clear();fileVersion++;submissionId=crypto.randomUUID();
  el('save').disabled=true;el('drawing').hidden=true;report('');
  el('editor-case').textContent=current.label+'　'+meta(current);el('editor').showModal();
}
el('add').onclick=()=>{if(account())showEditor();else openAccount(()=>{accountButton(el('account-entry'));showEditor();});};
el('close-editor').onclick=()=>el('editor').close();
el('editor').oncancel=e=>{if(uploading)e.preventDefault();};
el('editor').onclose=()=>{fileVersion++;editor.clear();};
async function selectFile(event) {
  const file=event.target.files[0];
  if(!file)return;
  const version=++fileVersion;editor.clear();el('drawing').hidden=true;el('save').disabled=true;report('写真を準備しています…');
  try {
    if(!await editor.load(file) || version!==fileVersion)return;
    el('drawing').hidden=false;el('save').disabled=false;report('');
  } catch{if(version===fileVersion)report('写真を開けませんでした。JPEGやPNGの画像を選び直してください。');}
  event.target.value='';
}
el('file').onchange=selectFile;el('camera').onchange=selectFile;
el('upload').onsubmit=async e=>{
  e.preventDefault();if(uploading||!current)return;
  if(!account()){openAccount(()=>{accountButton(el('account-entry'));report('ログインしました。保存を押してください。');});return;}
  const content=editor.snapshot();
  if(!content)return;
  const form=new FormData();form.set('action','upload');form.set('case_id',current.id);form.set('id',submissionId);
  form.set('image',content.blob,'entrance.jpg');form.set('arrows',JSON.stringify(content.arrows));form.set('note',el('note').value.trim());
  const controls=[...el('upload').querySelectorAll('button,input,textarea')];
  const disabled=controls.map(c=>c.disabled);
  controls.forEach(c=>c.disabled=true);el('canvas').inert=true;uploading=true;report('保存しています…');
  try{
    await request(form);el('editor').close();await listPhotos();
  }catch(error){report(error.message);if(error.status===401)openAccount(()=>{accountButton(el('account-entry'));report('ログインしました。保存を押してください。');});}
  finally{uploading=false;el('canvas').inert=false;controls.forEach((c,i)=>c.disabled=disabled[i]);}
};
const params=new URLSearchParams(location.search);
el('query').value=params.get('q')||'';
listCases(params.get('case_id'));
