const $=s=>document.querySelector(s);
const endpoint="https://evmgsqdrojxppxknrzfk.supabase.co/functions/v1/ippatsu-assistant";
let token=sessionStorage.getItem("ippatsu.chat.session")||"",history=[],busy=false;
function show(){const active=!!token;$("#welcome").hidden=active;$("#thread").hidden=!active;$("#lock").hidden=!active;}
function clear(){token="";history=[];sessionStorage.removeItem("ippatsu.chat.session");sessionStorage.removeItem("ippatsu.chat.pending");$("#messages").replaceChildren();show();}
async function api(action,data={}){
  let response;
  try{response=await fetch(endpoint,{method:"POST",headers:{"Content-Type":"application/json",...(token?{"x-ippatsu-session":token}:{})},body:JSON.stringify({action,...data}),cache:"no-store"});}
  catch{throw Error("通信できません。電波のよい場所で結果を確認してください。");}
  const result=await response.json();
  if(!response.ok){if(response.status===401&&token){clear();$("#notice").textContent="暗証番号をもう一度入力してください。";}throw Error(result.message||"処理できませんでした。");}
  return result;
}
function bubble(text,mine=false){const row=document.createElement("div");row.className=mine?"row mine":"row";
  if(!mine){const img=document.createElement("img");img.src="ippatsu.webp";img.alt="いっぱつちゃん";row.append(img);}
  const box=document.createElement("div");box.className="bubble";box.textContent=text;row.append(box);$("#messages").append(row);row.scrollIntoView({block:"nearest"});return box;}
function pending(id,text){sessionStorage.setItem("ippatsu.chat.pending",JSON.stringify({id,text}));}
function confirmation(id,text,check=false){
  const box=bubble(text),button=document.createElement("button");button.type="button";button.className="apply";box.append(button);
  button.textContent=check?"結果を読み直す":"この内容で反映";
  button.onclick=async()=>{
    button.disabled=true;
    try{const r=await api(check?"status":"apply",{id});
      if(r.state==="preview"){if(check){confirmation(id,r.summary);button.remove();return;}}
      bubble(r.message||r.summary);
      if(r.state==="queued"||r.state==="running"){check=!r.awaiting_dispatch;button.textContent=check?"結果を読み直す":"クラウド処理を開始";}
      else{button.remove();sessionStorage.removeItem("ippatsu.chat.pending");}
    }catch(e){bubble(e.message);check=true;button.textContent="受付結果を確認";}finally{button.disabled=false;}
  };
}
function start(){show();if(!token)return;
  bubble("どの現場のことかな？　日付や径間名、管理番号で聞いてね。");
  try{const p=JSON.parse(sessionStorage.getItem("ippatsu.chat.pending"));if(p)confirmation(p.id,p.text,true);}catch{}}
$("#login").onsubmit=async e=>{e.preventDefault();const b=$("#login button");b.disabled=true;$("#notice").textContent="";
  try{const r=await api("login",{pin:$("#pin").value});token=r.token;sessionStorage.setItem("ippatsu.chat.session",token);$("#pin").value="";start();}
  catch(e){$("#notice").textContent=e.message;}finally{b.disabled=false;}};
$("#lock").onclick=async()=>{try{await api("logout");}finally{clear();}};
async function send(text){if(!text||busy)return;busy=true;$("#compose button").disabled=true;$("#typing").hidden=false;
  bubble(text,true);history.push({role:"user",content:text});$("#message").value="";
  try{const r=await api("chat",{messages:history.slice(-11)});
    history.push({role:"assistant",content:r.message.slice(0,1800)});
    if(r.proposal){pending(r.proposal,r.message);confirmation(r.proposal,r.message);}else{
      const box=bubble(r.message);
      for(const item of r.links||[]){const url=new URL(item.url);
        if(url.origin!==location.origin||!url.pathname.startsWith("/ippatsu-share-pages/"))continue;
        const a=document.createElement("a");a.href=url.href;a.textContent=item.label;a.className="result-link";box.append(a);}
    }
  }catch(e){bubble(e.message);}finally{busy=false;$("#compose button").disabled=false;$("#typing").hidden=true;}}
$("#compose").onsubmit=e=>{e.preventDefault();send($("#message").value.trim());};
$("#message").onkeydown=e=>{if(e.key==="Enter"&&(e.ctrlKey||e.metaKey)&&!e.isComposing){e.preventDefault();send($("#message").value.trim());}};
$("#recent").onclick=async()=>{try{bubble((await api("recent")).message);}catch(e){bubble(e.message);}};
document.querySelectorAll(".suggestions button:not(#recent)").forEach(b=>b.onclick=()=>send(b.textContent));start();

