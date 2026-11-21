import {deviceCredential} from '../device.mjs';
import {call} from '../api.mjs';
const el=id=>document.getElementById(id);
const endpoint='https://evmgsqdrojxppxknrzfk.supabase.co/functions/v1/daily-photo';
const session='ippatsu.chat.session';
let selected=null,preview='',generation=0,id='',cursor=null;
async function api(action,form){
 const url=new URL(endpoint);url.searchParams.set('action',action);
 if(action==='list'&&cursor)url.searchParams.set('before',cursor);
 const r=await fetch(url,{method:'POST',headers:{'x-photo-device':await deviceCredential(),'x-ippatsu-session':sessionStorage.getItem(session)||''},body:form});
 if(r.status===401){sessionStorage.removeItem(session);lock();throw Error('暗証番号を入力してください。')}
 if(!r.ok)throw Error(r.status===507?'写真の保存枠がいっぱいです。':'通信結果を確認できません。ページを開き直して投稿を確認してください。');
 return r.json();
}
const sheet=el('sheet');
let writing=false,returnY=0;
sheet.addEventListener('close',()=>window.scrollTo({top:returnY,behavior:'instant'}));
function openSheet(post){
 writing=post;
 const signed=Boolean(sessionStorage.getItem(session));
 el('sheet-title').textContent=post?'写真を投稿':'リアクションする';
 el('unlock').hidden=signed;el('compose').hidden=!signed;
 el('sheet-status').textContent='';
 if(!sheet.open){returnY=window.scrollY;sheet.showModal();}
}
el('join').onclick=()=>openSheet(true);
el('dismiss').onclick=()=>sheet.close();
function lock(){openSheet(writing)}
function needLogin(){if(sessionStorage.getItem(session))return false;openSheet(false);return true}
function message(text){el(sheet.open?'sheet-status':'status').textContent=text}
el('name').value=localStorage.getItem('photo.nickname')||'';
function socials(card,p){
 const author=document.createElement('strong'),avatar=document.createElement('span'),head=document.createElement('div');
 const name=p.display_name||'以前の投稿';
 avatar.className='avatar';avatar.setAttribute('aria-hidden','true');avatar.textContent=Array.from(name)[0];
 avatar.dataset.tone=String(Array.from(name).reduce((n,c)=>n+c.codePointAt(0),0)%5);
 author.textContent=name;head.className='post-head';head.append(avatar,author,card.querySelector('time'));card.prepend(head);
 const like=document.createElement('button');like.className='reaction';
 function render(){like.setAttribute('aria-pressed',String(p.liked));like.textContent=(p.liked?'♥':'♡')+' いいね '+p.likes}
 render();card.append(like);like.onclick=async()=>{if(needLogin())return;like.disabled=true;try{Object.assign(p,await api('like',JSON.stringify({id:p.id,liked:!p.liked})));render()}catch(e){el('status').textContent=e.message}finally{like.disabled=false}};
 const thread=document.createElement('div');thread.className='comments';for(const c of [...p.comments].reverse()){const line=document.createElement('p'),by=document.createElement('strong');by.textContent=c.display_name;line.append(by,'　'+c.body);thread.append(line)}card.append(thread);
 const form=document.createElement('form'),input=document.createElement('input'),submit=document.createElement('button');form.className='respond';input.placeholder='ひと言コメント';input.setAttribute('aria-label','コメント');input.required=true;input.maxLength=140;submit.textContent='送る';form.append(input,submit);card.append(form);
 let requestId=crypto.randomUUID();form.onsubmit=async e=>{e.preventDefault();if(needLogin())return;const name=el('name').value.trim();if(!name){const nickname=prompt('コメントに使う表示名を入力してください。',localStorage.getItem('photo.nickname')||'')?.trim();if(nickname&&nickname.length<=24){el('name').value=nickname;form.requestSubmit()}return}submit.disabled=true;try{await api('comment',JSON.stringify({id:requestId,post_id:p.id,name,body:input.value}));localStorage.setItem('photo.nickname',name);requestId=crypto.randomUUID();await list(true)}catch(e){el('status').textContent=e.message}finally{submit.disabled=false}};
}
async function list(reset){
 if(reset)cursor=null;
 const {posts,next}=await api('list');
 if(reset){el('feed').replaceChildren();el('photo-strip').replaceChildren();}
 const strip=el('photo-strip');
 for(const p of posts){
  const card=document.createElement('article'),img=new Image(),text=document.createElement('p'),time=document.createElement('time');
  img.src=p.url;img.decoding='async';img.alt=p.caption;text.textContent=p.caption;time.dateTime=p.created_at;time.textContent=new Date(p.created_at).toLocaleString('ja-JP',{timeZone:'Asia/Tokyo',dateStyle:'medium',timeStyle:'short'});card.append(img,text,time);socials(card,p);card.id='photo-'+p.id;el('feed').append(card);
  if(strip.childElementCount<6){
   const jump=document.createElement('a'),thumb=new Image(),label=document.createElement('span');
   jump.href='#'+card.id;thumb.src=p.url;thumb.alt='';label.textContent=p.display_name||'以前の投稿';
   jump.setAttribute('aria-label',label.textContent+'の投稿へ：'+p.caption);jump.append(thumb,label);strip.append(jump);
  }
 }
 cursor=next;el('more').hidden=!cursor;
 if(!el('feed').children.length)el('status').textContent='最初の一枚を投稿してみよう。';
}
el('unlock').onsubmit=async e=>{e.preventDefault();try{const {token}=await call('login',{pin:e.target.elements.pin.value});sessionStorage.setItem(session,token);e.target.reset();if(writing)openSheet(true);else{sheet.close();message('操作できるようになりました。')}}catch(err){message(err.message)}};
async function resize(file){
 const img=new Image(),url=URL.createObjectURL(file);
 try{img.src=url;await img.decode();let size=Math.min(1,1440/Math.max(img.width,img.height));
 for(let i=0;i<6;i++,size*=.78){const canvas=document.createElement('canvas');canvas.width=Math.max(1,Math.round(img.width*size));canvas.height=Math.max(1,Math.round(img.height*size));const ctx=canvas.getContext('2d');ctx.fillStyle='white';ctx.fillRect(0,0,canvas.width,canvas.height);ctx.drawImage(img,0,0,canvas.width,canvas.height);const blob=await new Promise(resolve=>canvas.toBlob(resolve,'image/jpeg',.79));if(blob&&blob.size<=500000)return blob;}
 throw Error();
 }finally{URL.revokeObjectURL(url)}
}
el('photo').onchange=async e=>{const seq=++generation;selected=null;el('preview').hidden=true;URL.revokeObjectURL(preview);const file=e.target.files[0];if(!file)return;message('写真を小さくしています…');
 try{const blob=await resize(file);if(seq!==generation)return;selected=blob;id=crypto.randomUUID();el('preview').src=preview=URL.createObjectURL(blob);el('preview').hidden=false;message('');}
 catch{if(seq===generation)message('写真を読み込めません。JPEGなど別の画像を選んでください。')}};
el('compose').onsubmit=async e=>{e.preventDefault();if(!selected)return;const form=e.target,button=form.querySelector('button');if(button.disabled)return;button.disabled=true;
 try{const fd=new FormData();const name=el('name').value.trim();fd.set('name',name);fd.set('photo',selected,'photo.jpg');fd.set('caption',el('caption').value.trim());fd.set('id',id);await api('post',fd);selected=null;form.reset();localStorage.setItem('photo.nickname',name);el('name').value=name;el('preview').hidden=true;URL.revokeObjectURL(preview);sheet.close();message('投稿しました。');await list(true)}
 catch(err){message(err.message)}finally{button.disabled=false}};
el('more').onclick=async e=>{const button=e.currentTarget;button.disabled=true;try{await list(false)}catch(err){message(err.message)}finally{button.disabled=false}};
list(true).catch(e=>message(e.message));

