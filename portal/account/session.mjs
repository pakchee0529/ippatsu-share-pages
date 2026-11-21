import {offerClaim} from './claim.mjs';
const key='ippatsu.portal.account',session='ippatsu.chat.session';
const endpoint='https://evmgsqdrojxppxknrzfk.supabase.co/functions/v1/portal-account';
export {endpoint as accountEndpoint};
function read(store){
 try{const value=JSON.parse(store.getItem(key));if(value?.token&&Date.parse(value.expires)>Date.now())return value;if(value){if(sessionStorage.getItem(session)===value.token)sessionStorage.removeItem(session);store.removeItem(key)}}catch{store.removeItem(key)}
 return null;
}
export function account(){return read(sessionStorage)||read(localStorage)}
export function forget(){
 for(const storage of [sessionStorage,localStorage])storage.removeItem(key);
 for(const k of Object.keys(sessionStorage))if(k.startsWith('ippatsu.chat.'))sessionStorage.removeItem(k);
}
export function rotate(token){
 const a=account();if(!a)return;
 const store=a.remember?localStorage:sessionStorage;
 store.setItem(key,JSON.stringify({...a,token}));sessionStorage.setItem(session,token);
}
const initial=account();
if(initial)sessionStorage.setItem(session,initial.token);
window.addEventListener('storage',e=>{
 if(e.key!==key)return;
 if(!sessionStorage.getItem(key)){for(const k of Object.keys(sessionStorage))if(k.startsWith('ippatsu.chat.'))sessionStorage.removeItem(k);location.reload()}
});
export async function signOut(){
 const token=sessionStorage.getItem(session);if(token){
  const r=await fetch(endpoint.replace('portal-account','ippatsu-assistant'),{method:'POST',headers:{'Content-Type':'application/json','x-ippatsu-session':token},body:JSON.stringify({action:'logout'})});
  if(!r.ok&&r.status!==401)throw Error('通信を確認して、もう一度ログアウトしてください。');
 }
 forget();
}
export function openAccount(onSuccess=()=>location.reload()){
 const dialog=document.createElement('dialog');dialog.className='account-sheet';
 dialog.innerHTML='<form><h2 tabindex="-1" autofocus>共通アカウント</h2><p>砂場といっぱつちゃんで使えます。</p><label>利用者ID<input id="portal-account-username" autocapitalize="none" spellcheck="false" name="login" pattern="[A-Za-z0-9_\\-]{3,32}" autocomplete="username" required placeholder="例 tanaka01"></label><label>個人用の暗証番号・パスワード<input id="portal-account-password" name="password" autocapitalize="none" spellcheck="false" type="password" autocomplete="current-password" minlength="4" maxlength="72" required placeholder="4文字以上（数字だけでもOK）"></label><div hidden><label>表示名<input disabled autocomplete="nickname" name="name" maxlength="24"></label><label>会社の登録用暗証番号<input disabled data-1p-ignore data-lpignore="true" data-form-type="other" name="pin" inputmode="numeric" type="password" autocomplete="off"></label></div><label class="remember"><input name="remember" type="checkbox"> この端末で30日間ログインを維持</label><small>共用PCではチェックを外し、使い終わったらログアウトしてください。</small><p role="status"></p><footer style="display:grid;gap:.5rem"><button type="submit">ログイン</button><button type="button" class="switch">初めての方は登録</button><button type="button" class="close">閉じる</button></footer></form>';
 document.body.append(dialog);const form=dialog.querySelector('form'),fields=form.elements,group=form.querySelector('div'),send=form.querySelector('[type=submit]'),toggle=form.querySelector('.switch'),status=form.querySelector('[role=status]');
 const close=()=>dialog.close();form.querySelector('.close').onclick=close;dialog.onclose=()=>dialog.remove();
 toggle.onclick=()=>{group.hidden=!group.hidden;fields.namedItem('name').disabled=fields.pin.disabled=group.hidden;fields.namedItem('name').required=fields.pin.required=!group.hidden;if(group.hidden)fields.pin.value='';fields.password.autocomplete=group.hidden?'current-password':'new-password';send.textContent=group.hidden?'ログイン':'登録して使う';toggle.textContent=group.hidden?'初めての方は登録':'登録済みの方はログイン';status.textContent=''};
 let busy=false;form.onsubmit=async e=>{e.preventDefault();if(busy)return;busy=true;send.disabled=true;toggle.disabled=true;form.querySelector('.close').disabled=true;
 try{const remember=fields.remember.checked,body=Object.fromEntries(new FormData(form));const r=await fetch(endpoint,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({...body,action:group.hidden?'login':'register',remember})});const value=await r.json();
 if(!r.ok)throw Error(value.message||'ログインできませんでした。');
 forget();(remember?localStorage:sessionStorage).setItem(key,JSON.stringify({...value,remember}));sessionStorage.setItem(session,value.token);close();await offerClaim(value,endpoint);await onSuccess(value);
 }catch(err){status.textContent=err.message}finally{busy=false;send.disabled=false;toggle.disabled=false;form.querySelector('.close').disabled=false}};
 dialog.oncancel=e=>{if(busy)e.preventDefault()};dialog.showModal();
}
export function accountButton(button){
 const profile=account();
 button.textContent=profile?profile.name+'・ログアウト':'ログイン・登録';
 let claim=button.parentElement.querySelector('.device-claim');
 if(!claim&&profile){claim=document.createElement('button');claim.type='button';claim.className='device-claim';claim.textContent='端末から引き継ぐ';button.after(claim)}
 if(claim){claim.hidden=!profile;claim.onclick=async()=>{if(await offerClaim(profile,endpoint,true))location.reload()}}
 button.onclick=async()=>{if(!profile)return openAccount();try{await signOut();location.reload()}catch(e){alert(e.message)}};
}



