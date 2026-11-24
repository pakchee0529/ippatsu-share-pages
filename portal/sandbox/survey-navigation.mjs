import {originPicker,currentOrigin} from './survey-origin.mjs';
import {referenceContent,surveyWarnings} from './reference.mjs?v=size1';
import {overview,googleMapsUrl} from './overview.mjs?v=mapslinks2';
import {call} from './api.mjs';

const host = 'https://line-map-bot-ouvo.onrender.com';
const norm = s => s.normalize('NFKC').replace(/[〜～]/g,'~').replace(/\s/g,'');
function km(a,b){
  const r=Math.PI/180;
  return 12742*Math.asin(Math.sqrt(Math.sin((a[0]-b[0])*r/2)**2+
    Math.cos(a[0]*r)*Math.cos(b[0]*r)*Math.sin((a[1]-b[1])*r/2)**2));
}
function proposal(rows,origin,near){
  const todo=rows.filter(x=>x.center).sort((a,b)=>near?km(origin,a.center)-km(origin,b.center):km(origin,b.center)-km(origin,a.center));
  if(!todo.length)return rows;
  const route=[todo.shift()];
  while(todo.length){
    const last=route.at(-1).center;
    todo.sort((a,b)=>km(last,a.center)-km(last,b.center));
    route.push(todo.shift());
  }
  // Shorten crossed or backtracking legs while preserving the farthest first stop.
  for(let improved=true;improved;){
    improved=false;
    for(let i=1;i<route.length-1;i++)for(let j=i+1;j<route.length;j++){
      const a=route[i-1].center,b=route[i].center,c=route[j].center,d=route[j+1]?.center||origin;
      if(km(a,c)+km(b,d)+0.001<km(a,b)+km(c,d)){
        route.splice(i,j-i+1,...route.slice(i,j+1).reverse());improved=true;
      }
    }
  }
  return route.concat(rows.filter(x=>!x.center));
}
function node(tag,text){const el=document.createElement(tag);el.textContent=text;return el;}
function button(text,fn){const el=node('button',text);el.type='button';el.onclick=fn;return el;}
function mapLink(text,url){const a=node('a',text);a.href=url;a.target='_blank';a.rel='noopener noreferrer';return a;}
const mapAt=([lat,lng])=>host+'/map?'+new URLSearchParams({lat,lng});
function coordinate(value){
  if(!value||!/^[-\d.]+,[-\d.]+$/.test(value))return;
  const a=value.split(',').map(Number);
  if(a.every(Number.isFinite)&&Math.abs(a[0])<=90&&Math.abs(a[1])<=180)return a;
}
export function surveyNavigation(item,surface,shared){
  
  const doc=new DOMParser().parseFromString(item.definition.html,'text/html');
  if(!item.definition.title.includes('現調')&&!doc.querySelector('[data-survey-rows]'))return;
  const rows=[...doc.querySelectorAll('label')].map(label=>({
    name:label.textContent.trim(),review:label.dataset.review,reference:label.dataset.referenceNumber,key:label.querySelector('input[type=checkbox]')?.id
  })).filter(r=>r.key&&/[~～〜]/.test(r.name));
  if((!rows.length&&!doc.querySelector('[data-survey-rows]'))||new Set(rows.map(r=>r.key)).size!==rows.length)return;
  const heading=doc.querySelector('h1');
  const title=document.querySelector('#title');
  if(heading&&title){
    title.textContent=heading.textContent;
    const scale=Number(heading.querySelector('[data-edit-caption]')?.dataset.scale);
    if(scale>=.65&&scale<=3){const span=node('span',heading.textContent);span.style.fontSize=scale+'em';title.replaceChildren(span);}
  }
  const panel=node('section','');panel.className='survey-route';surface.before(panel);
  for(const section of doc.querySelectorAll('[data-survey-notices]')){
    const copy=node('section','');
    for(const line of section.children)copy.append(node(line.tagName==='H2'?'h2':'p',line.textContent));
    panel.append(copy);
  }
  const warningSummary=surveyWarnings(rows)||doc.querySelector('[data-survey-warning]')?.textContent;
  if(warningSummary)panel.append(node('p',warningSummary));
  const note=node('p','');
  note.setAttribute('role','status');
  const list=node('ol',''),actions=node('div',''),gps=node('p','');
  const orderKey='ippatsu.survey.order.'+item.id,visitKey='ippatsu.sandbox.inputs.'+item.id;
  let current=rows.slice(),suggested=[];
  let saved=[],visited={};
  try{saved=JSON.parse(localStorage.getItem(orderKey))||[];visited=JSON.parse(localStorage.getItem(visitKey))||{};}catch{}
  if(shared){visited={...shared.values};if(typeof visited.__route==="string"){try{saved=JSON.parse(visited.__route)}catch{saved=[]}}}
  // Older lists stored span names. Only unambiguous names can restore an old position.
  function rank(r){
    let i=saved.indexOf(r.key);
    if(i<0 && rows.filter(x=>x.name===r.name).length===1)i=saved.indexOf(r.name);
    return i<0?Infinity:i;
  }
  if(Array.isArray(saved))current.sort((a,b)=>rank(a)-rank(b));
  const lastKey='ippatsu.survey.last-check.'+item.id;
  function lastCheckedOrigin(){
    let key;try{key=localStorage.getItem(lastKey);}catch{}
    const row=current.find(r=>r.key===key&&visited[r.key]===true&&r.center);
    return row?{name:row.name,point:row.center,kind:'last'}:null;
  }
  const picker=originPicker(rows,lastCheckedOrigin);
  function route(near=false,point=picker.current().point){
    const remaining=proposal(current.filter(r=>!visited[r.key]),point,near);
    let i=0;
    return current.map(r=>visited[r.key]?r:remaining[i++]);
  }
  function invalidate(){plan.open=false;plan.hidden=true;accept.hidden=true;}
  function keep(){invalidate();const order=JSON.stringify(current.map(r=>r.key));shared?.save("__route",order);localStorage.setItem(orderKey,order);render();}
  function render(){drawMap(current,visited);list.replaceChildren();current.forEach((r,i)=>{
    const li=node('li',''),label=node('label',r.name),check=document.createElement('input');
    check.type='checkbox';check.checked=visited[r.key]===true;
    check.onchange=()=>{invalidate();visited[r.key]=check.checked;
      try{if(check.checked)localStorage.setItem(lastKey,r.key);else if(localStorage.getItem(lastKey)===r.key)localStorage.removeItem(lastKey);}catch{}
      shared?.save(r.key,check.checked);drawMap(current,visited);localStorage.setItem(visitKey,JSON.stringify(visited));};label.prepend(check);li.append(label);
    if(r.review)li.append(node('p',r.review));
    if(r.reference){const caption=node('small','');const size=Number(doc.querySelector('[data-survey-rows]')?.dataset.referenceSize);caption.append(referenceContent(r.reference,size>=12&&size<=48?size:null));li.append(caption);}
    const links=node('div','');
    if(r.center){links.append(mapLink('Googleマップ',googleMapsUrl(r.center)),mapLink('両端の電柱を見る',r.url),mapLink('200mの電柱',mapAt(r.center)));if(r.corrected)li.append(node('small','この電柱で合っていますか？ 読み取り：'+r.name+'　地図の候補：'+r.mapNames));}
    else if(rows.some(row=>row.center))li.append(node('small','座標を確認できません'));
    for(const [delta,text] of [[-1,'↑'],[1,'↓']]){
      const b=button(text,()=>{const j=i+delta;[current[i],current[j]]=[current[j],current[i]];keep();});b.disabled=i+delta<0||i+delta>=current.length;b.setAttribute('aria-label',r.name+'を'+(delta<0?'上へ':'下へ'));b.className='move';links.append(b);
    }
    li.append(links);list.append(li);
  });}
  const plan=node('details',''),summary=node('summary','巡回案を見る'),steps=node('ol','');plan.append(summary,steps);plan.hidden=true;
  const accept=button('この順番を採用',()=>{plan.open=false;plan.hidden=true;current=suggested.slice();keep();note.textContent='この巡回順を採用しました。';});accept.hidden=true;
  async function loadMaps(){
    note.textContent='地図で両端の電柱を探しています…';
    try{
      const cards=[];
      for(let i=0;i<rows.length;i+=10){
        const result=await call('poleSearch',{query:rows.slice(i,i+10).map(r=>r.name).join('\n')});
        if(!result.poleCards)throw Error(result.message||'電柱ナビに接続できません');
        cards.push(...result.poleCards);
      }
      for(const r of rows){
        const c=cards.find(c=>['found','corrected'].includes(c.status)&&norm(c.title)===norm(r.name));
        if(!c?.primary_url)continue;
        const u=new URL(c.primary_url),a=coordinate(u.searchParams.get('p1')),b=coordinate(u.searchParams.get('p2'));
        if(u.origin!==host||u.pathname!=='/multi-map'||!a||!b)continue;
        Object.assign(r,{center:a.map((n,i)=>(n+b[i])/2),url:u.href,corrected:c.status==='corrected',mapNames:[u.searchParams.get('p1n'),u.searchParams.get('p2n')].filter(Boolean).join('～')||c.title});
      }
      const count=rows.filter(r=>r.center).length;
      note.textContent='位置を確認できた径間 '+count+' / '+rows.length+'件';
      render();
    }catch(e){note.textContent=e.message;}
  }
  const match=button('おすすめの訪問順を見る',async()=>{
    match.disabled=true;
    try{
      await ready;
      if(!rows.some(r=>r.center))await loadMaps();
      const origin=await picker.choose();if(!origin)return;
      const todo=current.filter(r=>!visited[r.key]),known=todo.filter(r=>r.center);
      if(!known.length){invalidate();note.textContent=todo.length?'未訪問の径間の位置を確認できません。':'すべて訪問済みです。';return;}
      suggested=route(origin.kind!=='office',origin.point);
      const remaining=suggested.filter(r=>!visited[r.key]);
      const missing=remaining.filter(r=>!r.center).length;
      note.textContent='出発地点 '+origin.name+'。未訪問の'+known.length+'件を直線距離で並べました。'+(missing?'位置未確認の'+missing+'件は末尾です。':'');
      steps.replaceChildren(...remaining.map(r=>node('li',r.name+(r.center?'':'（位置未確認）'))));plan.hidden=false;plan.open=true;accept.hidden=false;
    }finally{match.disabled=false;}
  });
  const locate=button('現在地から200mの電柱',()=>{
    gps.replaceChildren();if(!navigator.geolocation){gps.textContent='現在地を取得できません';return;}
    locate.disabled=true;gps.textContent='位置を取得中…';
    navigator.geolocation.getCurrentPosition(p=>{locate.disabled=false;gps.replaceChildren(mapLink('現在地周辺の電柱地図を開く',mapAt([p.coords.latitude,p.coords.longitude])));},()=>{locate.disabled=false;gps.textContent='位置情報の許可と端末の設定を確認してください。';},{enableHighAccuracy:true,timeout:15000});
  });
  let editing=false;const edit=button('並べ替え',()=>{editing=!editing;panel.classList.toggle('reordering',editing);edit.textContent=editing?'並べ替えを終了':'並べ替え';edit.setAttribute('aria-pressed',String(editing));});const head=node('div','');head.className='survey-head';head.append(node('h2','訪問リスト'),edit);actions.className='survey-actions';actions.append(match,locate);plan.append(accept,button('巡回案を取り消す',()=>{invalidate();note.textContent='元の訪問順を維持しました。';}));panel.append(actions,gps,note,plan,head,list);const drawMap=overview(panel);surface.hidden=true;render();const ready=rows.length?loadMaps():Promise.resolve();
  function readVisited(){if(shared)return visited;try{return JSON.parse(localStorage.getItem(visitKey))||{};}catch{return visited;}}
  return {ready, next:()=>{const state=readVisited();return current.find(r=>!state[r.key]);}, checked:()=>{const state=readVisited();return current.filter(r=>state[r.key]);}, rows,
    route,chooseOrigin:picker.choose,currentOrigin,lastCheckedOrigin,
    applyRoute:route=>{current=route.slice();keep();}};
}



