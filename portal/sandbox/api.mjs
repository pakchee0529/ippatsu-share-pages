import {account,accountEndpoint} from '../account/session.mjs';
import {appearance,stamp,designBrief,reconcilePurpose} from './appearance.mjs';
import {deviceCredential} from './device.mjs';
export async function call(action,data={},onStep){
 const request=data.prompt;
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
 if(action==='sandboxDraft' && !data.template && !data.id && typeof data.prompt==='string' && data.prompt.length+designBrief.length+1<=1800){
   data={...data,prompt:data.prompt+'\n'+designBrief};
 }
 if(action==='sandboxPublish'){
   const prior=data.id?(await call('sandboxGet',{id:data.id})).definition:data.draft;
   const draft=stamp(data.draft,data.appearance||appearance(prior));
   data={...data,draft};
 }
 const device=await deviceCredential();
 if(action==='sandboxDraft')onStep?.('依頼を送信して、生成結果を待っています');
 const send=async()=>fetch(account()&&action.startsWith('sandbox')?accountEndpoint:'https://evmgsqdrojxppxknrzfk.supabase.co/functions/v1/ippatsu-assistant',{method:'POST',headers:{'Content-Type':'application/json','x-ippatsu-session':token},body:JSON.stringify({...data,action,device})});
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
 const result=await res.json();
 if(action==='sandboxDraft' && !data.id && result.draft)result.draft=reconcilePurpose(result.draft,request);
 return result;
}
export function linkFor(id){return new URL('tool.html?id='+encodeURIComponent(id),import.meta.url).href}
