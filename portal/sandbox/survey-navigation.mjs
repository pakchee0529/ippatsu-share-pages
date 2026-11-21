import {overview,googleMapsUrl} from './overview.mjs?v=mapslinks1';
import {call} from './api.mjs';

const office = [34.379692,135.672989]; // GSI address search: 上之町 representative point.
const host = 'https://line-map-bot-ouvo.onrender.com';
const norm = s => s.normalize('NFKC').replace(/[〜～]/g,'~').replace(/\s/g,'');
function km(a,b){
  const r=Math.PI/180;
  return 12742*Math.asin(Math.sqrt(Math.sin((a[0]-b[0])*r/2)**2+
    Math.cos(a[0]*r)*Math.cos(b[0]*r)*Math.sin((a[1]-b[1])*r/2)**2));
}
function proposal(rows){
  const todo=rows.filter(x=>x.center).sort((a,b)=>km(office,b.center)-km(office,a.center));
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
      const a=route[i-1].center,b=route[i].center,c=route[j].center,d=route[j+1]?.center||office;
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
export function surveyNavigation(item,surface){
  
  const doc=new DOMParser().parseFromString(item.definition.html,'text/html');
  if(!item.definition.title.includes('現調')&&!doc.querySelector('[data-survey-rows]'))return;
  const rows=[...doc.querySelectorAll('label')].map(label=>({
    name:label.textContent.trim(),review:label.dataset.review,reference:label.dataset.referenceNumber,key:label.querySelector('input[type=checkbox]')?.id
  })).filter(r=>r.key&&/[~～〜]/.test(r.name));
  if((!rows.length&&!doc.querySelector('[data-survey-rows]'))||new Set(rows.map(r=>r.name)).size!==rows.length)return;
  const panel=node('section','');panel.className='survey-route';surface.before(panel);
  const note=node('p','会社のある五條市上之町を起点に、遠い径間から回る順番を提案します。');
  note.setAttribute('role','status');
  const list=node('ol',''),actions=node('div',''),gps=node('p','');
  const orderKey='ippatsu.survey.order.'+item.id,visitKey='ippatsu.sandbox.inputs.'+item.id;
  let current=rows.slice(),suggested=[];
  let saved=[],visited={};
  try{saved=JSON.parse(localStorage.getItem(orderKey))||[];visited=JSON.parse(localStorage.getItem(visitKey))||{};}catch{}
  if(Array.isArray(saved))current.sort((a,b)=>(saved.includes(a.name)?saved.indexOf(a.name):Infinity)-(saved.includes(b.name)?saved.indexOf(b.name):Infinity));
  function keep(){localStorage.setItem(orderKey,JSON.stringify(current.map(r=>r.name)));render();}
  function render(){drawMap(current,visited);list.replaceChildren();current.forEach((r,i)=>{
    const li=node('li',''),label=node('label',r.name),check=document.createElement('input');
    check.type='checkbox';check.checked=visited[r.key]===true;
    check.onchange=()=>{visited[r.key]=check.checked;drawMap(current,visited);localStorage.setItem(visitKey,JSON.stringify(visited));};label.prepend(check);li.append(label);
    if(r.review)li.append(node('p',r.review));
    if(r.reference)li.append(node('small',r.reference));
    const links=node('div','');
    if(r.center){links.append(mapLink('両端の電柱を見る',r.url),mapLink('Google マップで開く',googleMapsUrl(r.center)),mapLink('径間の中点から200mの電柱',mapAt(r.center)));if(r.corrected)li.append(node('small','この電柱で合っていますか？ 読み取り：'+r.name+'　地図の候補：'+r.mapNames));}
    else if(suggested.length)li.append(node('small','座標を確認できません'));
    for(const [delta,text] of [[-1,'↑'],[1,'↓']]){
      const b=button(text,()=>{const j=i+delta;[current[i],current[j]]=[current[j],current[i]];keep();});b.disabled=i+delta<0||i+delta>=current.length;b.setAttribute('aria-label',r.name+'を'+(delta<0?'上へ':'下へ'));b.className='move';links.append(b);
    }
    li.append(links);list.append(li);
  });}
  const plan=node('details',''),summary=node('summary','巡回案を見る'),steps=node('ol','');plan.append(summary,steps);plan.hidden=true;
  const accept=button('この順番を採用',()=>{plan.open=false;plan.hidden=true;current=suggested.slice();keep();note.textContent='この端末に巡回順を保存しました。';});accept.hidden=true;
  const match=button('おすすめの訪問順を見る',async(event)=>{
    match.disabled=true;note.textContent='地図で両端の電柱を探しています…';
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
      suggested=proposal(rows);const count=rows.filter(r=>r.center).length;
      note.textContent=(count===rows.length?count+'件すべて':rows.length+'件のうち'+count+'件')+'で両端の電柱が見つかりました。訪問順は、会社のある上之町を仮の出発点にして、直線距離で計算しています。';steps.replaceChildren(...suggested.map(r=>node('li',r.name)));plan.hidden=!count;plan.open=!!count&&event?.isTrusted===true;
      accept.hidden=!count;render();
    }catch(e){note.textContent=e.message;}finally{match.disabled=false;}
  });
  const locate=button('現在地から200mの電柱',()=>{
    gps.replaceChildren();if(!navigator.geolocation){gps.textContent='現在地を取得できません';return;}
    locate.disabled=true;gps.textContent='位置を取得中…';
    navigator.geolocation.getCurrentPosition(p=>{locate.disabled=false;gps.replaceChildren(mapLink('現在地周辺の電柱地図を開く',mapAt([p.coords.latitude,p.coords.longitude])));},()=>{locate.disabled=false;gps.textContent='位置情報の許可と端末の設定を確認してください。';},{enableHighAccuracy:true,timeout:15000});
  });
  let editing=false;const edit=button('並べ替え',()=>{editing=!editing;panel.classList.toggle('reordering',editing);edit.textContent=editing?'並べ替えを終了':'並べ替え';edit.setAttribute('aria-pressed',String(editing));});const head=node('div','');head.className='survey-head';head.append(node('h2','訪問リスト'),edit);actions.className='survey-actions';actions.append(match,locate);plan.append(accept);panel.append(actions,gps,note,plan,head,list);const drawMap=overview(panel);surface.hidden=true;render();const ready=rows.length?match.onclick():Promise.resolve();
  function readVisited(){try{return JSON.parse(localStorage.getItem(visitKey))||{};}catch{return visited;}}
  return {ready, next:()=>{const state=readVisited();return current.find(r=>!state[r.key]);}, checked:()=>{const state=readVisited();return current.filter(r=>state[r.key]);}, rows,
    route:(near=false)=>near?current.slice().sort((a,b)=>(a.center?km(office,a.center):Infinity)-(b.center?km(office,b.center):Infinity)):suggested.slice(),
    applyRoute:route=>{current=route.slice();keep();}};
}



