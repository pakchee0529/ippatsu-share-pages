import {call} from '../api.mjs';
const el=id=>document.getElementById(id);
const endpoint='https://evmgsqdrojxppxknrzfk.supabase.co/functions/v1/daily-photo';
const session='ippatsu.chat.session';
let selected=null,preview='',generation=0,id='',cursor=null;
async function api(action,form){
 const url=new URL(endpoint);url.searchParams.set('action',action);
 if(action==='list'&&cursor)url.searchParams.set('before',cursor);
 const r=await fetch(url,{method:'POST',headers:{'x-ippatsu-session':sessionStorage.getItem(session)||''},body:form});
 if(r.status===401){sessionStorage.removeItem(session);lock();throw Error('暗証番号を入力してください。')}
 if(!r.ok)throw Error(r.status===507?'写真の保存枠がいっぱいです。':'通信結果を確認できません。ページを開き直して投稿を確認してください。');
 return r.json();
}
function lock(){el('unlock').hidden=false;el('compose').hidden=true;el('feed').replaceChildren();el('more').hidden=true;cursor=null}
async function list(reset){
 if(reset)cursor=null;
 const {posts}=await api('list');if(reset)el('feed').replaceChildren();
 for(const p of posts){
  const card=document.createElement('article'),img=new Image(),text=document.createElement('p'),time=document.createElement('time');
  img.src=p.url;img.alt=p.caption;text.textContent=p.caption;time.dateTime=p.created_at;time.textContent=new Date(p.created_at).toLocaleString('ja-JP',{timeZone:'Asia/Tokyo',dateStyle:'medium',timeStyle:'short'});card.append(img,text,time);el('feed').append(card);
 }
 cursor=posts.at(-1)?.created_at;el('more').hidden=posts.length<12;
 if(!el('feed').children.length)el('status').textContent='最初の一枚を投稿してみよう。';
}
async function start(){el('unlock').hidden=true;el('compose').hidden=false;try{await list(true)}catch(e){el('status').textContent=e.message}}
el('unlock').onsubmit=async e=>{e.preventDefault();try{const {token}=await call('login',{pin:e.target.elements.pin.value});sessionStorage.setItem(session,token);e.target.reset();el('status').textContent='';await start()}catch(err){el('status').textContent=err.message}};
async function resize(file){
 const img=new Image(),url=URL.createObjectURL(file);
 try{img.src=url;await img.decode();let size=Math.min(1,1440/Math.max(img.width,img.height));
 for(let i=0;i<6;i++,size*=.78){const canvas=document.createElement('canvas');canvas.width=Math.max(1,Math.round(img.width*size));canvas.height=Math.max(1,Math.round(img.height*size));const ctx=canvas.getContext('2d');ctx.fillStyle='white';ctx.fillRect(0,0,canvas.width,canvas.height);ctx.drawImage(img,0,0,canvas.width,canvas.height);const blob=await new Promise(resolve=>canvas.toBlob(resolve,'image/jpeg',.79));if(blob&&blob.size<=500000)return blob;}
 throw Error();
 }finally{URL.revokeObjectURL(url)}
}
el('photo').onchange=async e=>{const seq=++generation;selected=null;el('preview').hidden=true;URL.revokeObjectURL(preview);const file=e.target.files[0];if(!file)return;el('status').textContent='写真を小さくしています…';
 try{const blob=await resize(file);if(seq!==generation)return;selected=blob;id=crypto.randomUUID();el('preview').src=preview=URL.createObjectURL(blob);el('preview').hidden=false;el('status').textContent='';}
 catch{if(seq===generation)el('status').textContent='写真を読み込めません。JPEGなど別の画像を選んでください。'}};
el('compose').onsubmit=async e=>{e.preventDefault();if(!selected)return;const form=e.target,button=form.querySelector('button');if(button.disabled)return;button.disabled=true;
 try{const fd=new FormData();fd.set('photo',selected,'photo.jpg');fd.set('caption',el('caption').value.trim());fd.set('id',id);await api('post',fd);selected=null;form.reset();el('preview').hidden=true;URL.revokeObjectURL(preview);el('status').textContent='投稿しました。';await list(true)}
 catch(err){el('status').textContent=err.message}finally{button.disabled=false}};
el('more').onclick=async e=>{const button=e.currentTarget;button.disabled=true;try{await list(false)}catch(err){el('status').textContent=err.message}finally{button.disabled=false}};
if(sessionStorage.getItem(session))start();else lock();
