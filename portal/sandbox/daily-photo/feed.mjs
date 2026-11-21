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
 if(r.status===401){sessionStorage.removeItem(session);throw Object.assign(Error('暗証番号を入力してください。'),{status:401})}
 if(r.status===409)throw Error('投稿が更新されました。開き直して確認してください。');
 if(!r.ok)throw Error(r.status===507?'写真の保存枠がいっぱいです。':'通信結果を確認できません。ページを開き直して投稿を確認してください。');
 return r.json();
}
const sheet=el('sheet');
let writing=false,returnY=0,resume=null;
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
el('dismiss').onclick=()=>{resume=null;sheet.close()};
sheet.oncancel=()=>{resume=null};
function askToResume(fn){resume=fn;openSheet(false)}
async function withLogin(fn){
 if(!sessionStorage.getItem(session)){askToResume(fn);return}
 try{await fn()}catch(err){if(err.status===401)askToResume(fn);else message(err.message)}
}
const viewer=el('viewer');
el('viewer-close').onclick=()=>viewer.close();
viewer.onclick=e=>{if(e.target===viewer)viewer.close()};
function photoButton(img,p){
 const button=document.createElement('button');button.type='button';button.className='photo-open';
 button.setAttribute('aria-label','写真を拡大：'+p.caption);button.setAttribute('aria-haspopup','dialog');
 button.append(img);button.onclick=()=>{el('full-photo').src=img.currentSrc||img.src;el('full-photo').alt=p.caption;el('full-caption').textContent=p.caption;viewer.showModal()};
 return button;
}
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
 render();card.append(like);like.onclick=()=>{const liked=!p.liked;withLogin(async()=>{
  like.disabled=true;try{Object.assign(p,await api('like',JSON.stringify({id:p.id,liked})));render()}finally{like.disabled=false}
 })};
 const thread=document.createElement('div');
 thread.className='comments';
 function showComment(name,body){
  const line=document.createElement('p'),by=document.createElement('strong');
  by.textContent=name;line.append(by,'　'+body);thread.append(line);
  if(thread.childElementCount>5)thread.firstElementChild.remove();
 }
 for(const c of [...p.comments].reverse())showComment(c.display_name,c.body);
 const toggle=document.createElement('button'),form=document.createElement('form');
 const input=document.createElement('input'),submit=document.createElement('button');
 toggle.type='button';toggle.className='comment-toggle';
 form.id='reply-'+p.id;form.className='respond';toggle.setAttribute('aria-controls',form.id);
 input.placeholder='ひと言コメント';input.setAttribute('aria-label','コメント');
 input.required=true;input.maxLength=140;submit.textContent='送る';form.append(input,submit);
 function expand(open){
  form.hidden=!open;toggle.setAttribute('aria-expanded',String(open));
  toggle.textContent=open?'閉じる':'コメントする';
  if(open)input.focus();
 }
 expand(false);like.after(toggle);card.append(thread,form);
 toggle.onclick=()=>{expand(form.hidden)};
 input.onkeydown=e=>{if(e.key==='Escape'&&!e.isComposing){expand(false);toggle.focus()}};
 let requestId=crypto.randomUUID();
 form.onsubmit=async e=>{
  e.preventDefault();if(submit.disabled)return;
  if(!sessionStorage.getItem(session)){askToResume(()=>form.requestSubmit());return}
  let name=el('name').value.trim();
  if(!name){
   name=prompt('コメントに使う表示名を入力してください。',localStorage.getItem('photo.nickname')||'')?.trim();
   if(!name||name.length>24)return;
   el('name').value=name;
  }
  const body=input.value.trim();if(!body){input.focus();return}
  submit.disabled=true;input.readOnly=true;
  try{
   await api('comment',JSON.stringify({id:requestId,post_id:p.id,name,body}));
   localStorage.setItem('photo.nickname',name);requestId=crypto.randomUUID();
   showComment(name,body);input.value='';expand(false);toggle.focus();
  }catch(err){if(err.status===401)askToResume(()=>form.requestSubmit());else message(err.message)}finally{submit.disabled=false;input.readOnly=false}
 };

}
function ownerMenu(card,p){
 if(!p.owned)return;
 const menu=document.createElement('details'),label=document.createElement('summary');
 label.textContent='自分の投稿を管理';menu.append(label);
 for(const [action,title] of [['edit','ひと言を編集'],['withdraw','取り下げる']]){
  const button=document.createElement('button');button.textContent=title;menu.append(button);
  button.onclick=()=>{
   const data={id:p.id};
   if(action==='edit'){
    const value=prompt('ひと言を編集',p.caption)?.trim();
    if(!value||value===p.caption)return;
    if(value.length>140){message('ひと言は140文字までです。');return}
    Object.assign(data,{caption:value,previous:p.caption});
   }else if(!confirm('この写真と、付いたコメント・いいねを取り下げますか？'))return;
   withLogin(async()=>{await api(action,JSON.stringify(data));await list(true);await refreshInbox()});
  };
 }
 card.append(menu);
}
async function refreshInbox(){
 const {items}=await api('unread');const box=el('inbox');box.replaceChildren();
 for(const item of items){
  const button=document.createElement('button');
  button.textContent='新しいコメント '+item.unread+'件　'+item.caption;
  button.onclick=async()=>{
   button.disabled=true;
   try{
    const key='photo-'+item.id;
    while(!el(key)&&cursor)await list(false);
    const thread=el(key)?.querySelector('.comments');
    if(thread){thread.tabIndex=-1;thread.focus();thread.scrollIntoView({block:'center'});await api('seen',JSON.stringify({id:item.id,latest:item.latest}));}
    await refreshInbox();
   }catch(err){message(err.message)}finally{button.disabled=false}
  };
  box.append(button);
 }
}
async function list(reset){
 if(reset)cursor=null;
 const {posts,next}=await api('list');
 if(reset){el('feed').replaceChildren();el('photo-strip').replaceChildren();}
 const strip=el('photo-strip');
 for(const p of posts){
  const card=document.createElement('article'),img=new Image(),text=document.createElement('p'),time=document.createElement('time');
  img.src=p.url;img.decoding='async';img.alt=p.caption;text.textContent=p.caption;time.dateTime=p.created_at;time.textContent=new Date(p.created_at).toLocaleString('ja-JP',{timeZone:'Asia/Tokyo',dateStyle:'medium',timeStyle:'short'});card.append(photoButton(img,p),text,time);socials(card,p);ownerMenu(card,p);card.id='photo-'+p.id;el('feed').append(card);
  if(strip.childElementCount<6){
   const jump=document.createElement('a'),thumb=new Image(),label=document.createElement('span');
   jump.href='#'+card.id;thumb.src=p.url;thumb.alt='';label.textContent=p.display_name||'以前の投稿';
   jump.setAttribute('aria-label',label.textContent+'の投稿へ：'+p.caption);jump.append(thumb,label);strip.append(jump);
  }
 }
 cursor=next;el('more').hidden=!cursor;
 if(!el('feed').children.length)el('status').textContent='最初の一枚を投稿してみよう。';
}
el('unlock').onsubmit=async e=>{e.preventDefault();try{const {token}=await call('login',{pin:e.target.elements.pin.value});sessionStorage.setItem(session,token);e.target.reset();if(writing)openSheet(true);else{const fn=resume;resume=null;sheet.close();if(fn)await withLogin(fn)}}catch(err){message(err.message)}};
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
 catch(err){if(err.status===401)openSheet(true);message(err.message)}finally{button.disabled=false}};
el('more').onclick=async e=>{const button=e.currentTarget;button.disabled=true;try{await list(false)}catch(err){if(err.status===401)openSheet(true);message(err.message)}finally{button.disabled=false}};
Promise.all([list(true),refreshInbox()]).catch(e=>message(e.message));

