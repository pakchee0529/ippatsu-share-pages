import {renderMap} from './map.mjs';
const el=id=>document.getElementById(id);
const dialog=el('viewer');
let current=null;
function showMedia(camera){
  const screen=el('screen'), state=el('state');
  screen.replaceChildren();el('refresh').hidden=camera.mediaType!=='image';
  if(!camera.media){state.textContent=camera.status||'映像は配信元のページで確認できます。';return;}
  const tag={image:'img',iframe:'iframe',video:'video'}[camera.mediaType];
  if(!tag){state.textContent=camera.status||'映像は配信元のページで確認できます。';return;}
  const media=document.createElement(tag);
  state.textContent='配信元から読み込んでいます…';
    async function loaded(){
    if(!media.isConnected)return;
    state.textContent='撮影時刻は配信元の表示を確認してください。';
    if(!camera.timestampUrl)return;
    try{
      const response=await fetch(camera.timestampUrl,{cache:'no-store',signal:AbortSignal.timeout(8000)});
      if(!response.ok)return;
      const info=await response.json(), at=new Date(info.create_time||info.get_time);
      if(!(info.create_time||info.get_time)||!Number.isFinite(at.getTime())||!media.isConnected)return;
      const stamp=new Intl.DateTimeFormat('ja-JP',{timeZone:'Asia/Tokyo',month:'numeric',day:'numeric',hour:'2-digit',minute:'2-digit'}).format(at);
      state.textContent=(info.create_time?'撮影 ':'配信元の取得 ')+stamp+'（日本時間）'+(Date.now()-at.getTime()>3600000?'　1時間以上前の画像です。':'');
    }catch{/* Keep the source guidance on connection failure. */}
  }
  media.onload=loaded; media.onloadeddata=loaded;
  media.onerror=()=>{if(media.isConnected){state.textContent='画像を表示できません。配信元で最新の状況を確認してください。';media.remove();}};
  if(tag==='img')media.alt=camera.name+'のカメラ画像';
  if(tag==='iframe'){media.title=camera.name+'の公式映像';media.allowFullscreen=true;}
  if(tag==='video'){media.controls=true;media.playsInline=true;}
  media.src=camera.media;
  screen.append(media);
}
function pick(camera){
  current=camera;
  el('area').textContent=camera.area;el('name').textContent=camera.name;
  el('credit').textContent=[camera.provider,camera.kind,({image:'更新画像',video:'動画',iframe:'公式ビュー'})[camera.mediaType],camera.status].filter(Boolean).join(' ／ ');
  el('official').href=camera.source;
  if(!dialog.open)dialog.showModal();showMedia(camera);
}
el('refresh').onclick=()=>{if(current)showMedia(current)};
el('close').onclick=()=>dialog.close();dialog.onclose=()=>{current=null;el('screen').replaceChildren()};
try{
  const cameras=(await Promise.all(['west','east'].map(async region=>{
    const response=await fetch('./'+region+'.json');if(!response.ok)throw Error();return response.json();
  }))).flat();
  for(const area of [...new Set(cameras.map(c=>c.area))]){
    const section=document.createElement('details'),summary=document.createElement('summary');
    const members=cameras.filter(c=>c.area===area);
    summary.textContent=area+'（'+members.length+'）';section.append(summary);
    for(const camera of members){const button=document.createElement('button');button.textContent=camera.name+(camera.status?'（'+camera.status+'）':'');button.onclick=()=>pick(camera);section.append(button);}
    el('list').append(section);
  }
  el('status').textContent='';
  try{await renderMap(el('map'),cameras,pick);}catch{el('status').textContent='地図を読み込めません。下の地域一覧から選べます。';}
}catch{el('status').textContent='カメラ一覧を取得できません。ページを開き直してください。';}
