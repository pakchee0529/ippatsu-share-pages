import {deviceCredential} from './device.mjs';
export async function call(action,data={}){
 const token=sessionStorage.getItem('ippatsu.chat.session');
 if(!token&&action!=='login')throw Error('いっぱつちゃんで暗証番号を入力してから開いてください');
 const res=await fetch('https://evmgsqdrojxppxknrzfk.supabase.co/functions/v1/ippatsu-assistant',{method:'POST',headers:{'Content-Type':'application/json','x-ippatsu-session':token},body:JSON.stringify({...data,action,device:await deviceCredential()})});
 const result=await res.json();if(!res.ok){const error=Error(result.message||'通信に失敗しました');error.status=res.status;throw error;}return result;
}
export function linkFor(id){return new URL('tool.html?id='+encodeURIComponent(id),import.meta.url).href}
