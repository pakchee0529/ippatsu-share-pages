import {account, accountButton, openAccount} from '../../account/session.mjs';
import {mountMap} from './map.mjs';

const el = id => document.getElementById(id);
const editor = el('editor');
const vehicles = ['軽トラ', '普通車', '2t車'];
let map, spots = [], target, requestId, busy = false;
accountButton(el('account-entry'));

async function api(action, data = {}) {
  const response = await fetch('https://evmgsqdrojxppxknrzfk.supabase.co/functions/v1/lunch-map', {
    method:'POST', headers:{'Content-Type':'application/json','x-ippatsu-session':account()?.token || ''},
    body:JSON.stringify({action,...data})
  });
  const result = await response.json();
  if (!response.ok) throw Error(result.message || '通信できませんでした。もう一度お試しください。');
  return result;
}
function node(tag, text) {
  const element = document.createElement(tag);
  element.textContent = text;
  return element;
}
for (const vehicle of vehicles) {
  const label = node('label',vehicle);
  const input = document.createElement('input');
  Object.assign(input,{type:'number',min:'0',max:'99',step:'1',name:vehicle,placeholder:'台'});
  label.append(input);
  el('vehicles').append(label);
}
function card(spot) {
  const article = document.createElement('article');
  article.id = 'spot-'+spot.id;
  article.append(node('h3',spot.name),node('p',spot.pole ? '最寄りの電柱　'+spot.pole : '最寄りの電柱は未確認'));
  const link=node('a','Googleマップ');
  link.href='https://www.google.com/maps/search/?api=1&query='+encodeURIComponent(spot.lat+','+spot.lng);
  link.className='route'; link.target='_blank'; link.rel='noopener';
  const add=node('button','レビューを書く');
  add.onclick=()=>start(spot);
  article.append(link,add);
  for (const review of spot.reviews) {
    const block=document.createElement('div'); block.className='review';
    const counts=Object.entries(review.capacities).map(([type,count])=>type+' '+count+'台').join(' ／ ');
    block.append(node('strong',[review.season,review.time].filter(Boolean).join('の') || '季節・時間帯は未確認'),node('p',counts || '駐車台数は未確認'));
    if(review.note) block.append(node('p',review.note));
    block.append(node('small',review.author+'　'+new Date(review.created_at).toLocaleDateString('ja-JP',{timeZone:'Asia/Tokyo'})));
    article.append(block);
  }
  return article;
}
async function refresh() {
  ({spots}=await api('list'));
  map?.setSpots(spots);
  el('spots').replaceChildren(...spots.map(card));
  if(!spots.length) el('spots').textContent='まだ投稿はありません。地図をタップすると最初の場所を登録できます。';
}
function start(place) {
  if(!account()) return openAccount(()=>{accountButton(el('account-entry'));start(place)});
  target=place; requestId=crypto.randomUUID(); editor.reset();
  el('heading').textContent=place.id ? place.name+'のレビュー' : '休憩スポットを登録';
  el('position').textContent=place.pole ? '最寄りの電柱　'+place.pole : '最寄りの電柱は未確認';
  el('name-label').hidden=Boolean(place.id);
  editor.elements.name.required=!place.id;
  el('error').textContent='';
  el('edit').showModal();
}
el('cancel').onclick=()=>el('edit').close();
el('edit').oncancel=e=>{if(busy)e.preventDefault()};
editor.onsubmit=async e=>{
  e.preventDefault(); if(busy)return;
  const values=new FormData(editor);
  const capacities=Object.fromEntries(vehicles.filter(v=>values.get(v)!=='').map(v=>[v,Number(values.get(v))]));
  const review={capacities,season:values.get('season'),time:values.get('time'),note:values.get('note').trim()};
  if (!Object.keys(capacities).length && !review.season && !review.time && !review.note) { el('error').textContent='台数・季節・時間帯・ひと言のどれかを入力してください。'; return; }
  const place=target; busy=true; el('save').disabled=el('cancel').disabled=true;
  try {
    if(place.id) await api('review',{id:requestId,spot_id:place.id,review});
    else await api('create',{id:requestId,name:values.get('name').trim(),lat:place.lat,lng:place.lng,pole:place.pole||'',review});
    el('edit').close();
    el('status').textContent='投稿しました。';
    try {await refresh()} catch {el('status').textContent='投稿しました。一覧を再読み込みしてください。'}
  } catch(error){el('error').textContent=error.message}
  finally{busy=false;el('save').disabled=el('cancel').disabled=false}
};
el('locate').onclick=async()=>{try{await map?.locate()}catch(e){el('status').textContent=e.message}};
try {
  map=await mountMap(el('map'),start,id=>el('spot-'+id)?.scrollIntoView({behavior:'smooth',block:'start'}));
} catch {el('status').textContent='地図を読み込めませんでした。ページを開き直してください。'}
try {await refresh()} catch(e){el('spots').textContent=e.message}
