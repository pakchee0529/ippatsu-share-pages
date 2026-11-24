import {account,accountEndpoint} from '../account/session.mjs';
import {appearance,stamp,designBrief,reconcilePurpose} from './appearance.mjs';
import {preparePhoto,usesAttachedPhoto} from './attached-photo.mjs';
import {deviceCredential} from './device.mjs';
import {artBrief,matchesArt} from './generated-art.mjs';

// Retry only the illustration when the HTML generation already succeeded.
let imageRetry=null;
async function requestKey(body,token){
 const digest=await crypto.subtle.digest('SHA-256',new TextEncoder().encode(token+'\n'+body));
 return Array.from(new Uint8Array(digest),v=>v.toString(16).padStart(2,'0')).join('');
}
export async function call(action,data={},onStep){
 const request=data.prompt;
 const previousPhoto=data.previous?.photo;
 const previousArt=data.previous?.generatedArt;
 if(action==='sandboxDraft' && (previousArt||data.previous?.photo)){
   const {photo,generatedArt,...previous}=data.previous;
   data={...data,previous};
 }
 const token=sessionStorage.getItem('ippatsu.chat.session');
 if(!token&&(action==='sandboxGet'||action==='sandboxList')){
   const url=new URL('https://evmgsqdrojxppxknrzfk.supabase.co/functions/v1/daily-photo');
   url.searchParams.set('action',action==='sandboxGet'?'page':'directory');
   if(data.id)url.searchParams.set('id',data.id);
   const response=await fetch(url,{method:'POST'});
   if(!response.ok)throw Error('ページを読み込めませんでした。');
   return response.json();
 }
 if(!token&&action!=='login')throw Error('いっぱつちゃんで暗証番号を入力してから開いてください');
 if(action==='sandboxDraft' && data.turnProtocol!==1 && !data.template && !data.id && typeof data.prompt==='string' && data.prompt.length+designBrief.length+1<=1800){
   data={...data,prompt:data.prompt+'\n'+designBrief};
 }
 if(action==='sandboxPublish'){
   const brief=artBrief(data.draft?.html);
   if(brief&&!matchesArt(data.draft.generatedArt,brief))throw Error('挿絵を準備してから掲載してください。');
   const prior=data.id?(await call('sandboxGet',{id:data.id})).definition:data.draft;
   const draft=stamp(data.draft,data.appearance||appearance(prior));
   data={...data,draft};
 }
 const device=await deviceCredential();
 if(action==='sandboxDraft')onStep?.('依頼を送信して、生成結果を待っています');
 const body=JSON.stringify({...data,action,device});
 const key=action==='sandboxDraft'?await requestKey(body,token):null;
 let result=key && key===imageRetry?.key?imageRetry.result:null;
 if(!result){
   const send=async()=>fetch(account()&&action.startsWith('sandbox')?accountEndpoint:'https://evmgsqdrojxppxknrzfk.supabase.co/functions/v1/ippatsu-assistant',{method:'POST',headers:{'Content-Type':'application/json','x-ippatsu-session':token},body});
   let res;
   try{res=await send();}
   catch(error){
     if(action!=='sandboxDraft'||!(error instanceof TypeError))throw error;
     onStep?.('通信の回復を待って、下書きの依頼を送り直します');
     await new Promise(resolve=>{
       function ready(){clearTimeout(timer);window.removeEventListener('online',ready);resolve();}
       const timer=setTimeout(ready,navigator.onLine?1500:15000);
       window.addEventListener('online',ready,{once:true});
     });
     res=await send();
   }
   if(action==='sandboxDraft')onStep?.('サーバーの応答を読み込んでいます');
   if(!res.ok){const detail=await res.json().catch(()=>({}));const error=Error(detail.message||'通信に失敗しました');error.status=res.status;throw error;}
   result=await res.json();
 }
 if(action==='sandboxDraft' && result.draft && usesAttachedPhoto(result.draft.html)){
   const source=data.image||previousPhoto||(data.id && (await call('sandboxGet',{id:data.id})).definition.photo);
   if(!source)throw Error('このページに表示する写真を添付してください。');
   result.draft.photo=await preparePhoto(source);
 }
 if(action==='sandboxDraft' && result.draft){
   const brief=artBrief(result.draft.html);
   if(brief){
     let prior=result.kind==='newDraft'?null:previousArt;
     if(!prior&&data.id&&result.kind!=='newDraft')prior=(await call('sandboxGet',{id:data.id})).definition.generatedArt;
     if(matchesArt(prior,brief))result.draft.generatedArt=prior;
     else {
       imageRetry={key,result};
       onStep?.('このページに合う挿絵を描いています');
       try{
         const {image}=await call('sandboxGenerateArt',{brief});
         if(!matchesArt({brief,image},brief))throw Error('生成画像を読み込めませんでした。');
         result.draft.generatedArt={brief,image};
       }catch(error){
         throw Error('ページの下書きはできました。挿絵の生成をもう一度試せます。 '+error.message);
       }
     }
   }
   if(imageRetry?.key===key)imageRetry=null;
 }
 if(action==='sandboxDraft' && !data.id && result.draft)result.draft=reconcilePurpose(result.draft,request);
 return result;
}
export function linkFor(id){return new URL('tool.html?id='+encodeURIComponent(id),import.meta.url).href}
