const $=s=>document.querySelector(s);
// Mobile keyboards and in-app browser controls can shrink only the visual viewport.
const viewport = window.visualViewport;
function fitChat() {
  if (viewport && viewport.scale === 1 && viewport.height > 0) {
    document.documentElement.style.setProperty("--chat-visible-height", Math.floor(viewport.height) + "px");
  }
}
fitChat();
viewport?.addEventListener("resize", fitChat);
window.addEventListener("pageshow", fitChat);
const endpoint="https://evmgsqdrojxppxknrzfk.supabase.co/functions/v1/ippatsu-assistant";
let token=sessionStorage.getItem("ippatsu.chat.session")||"",history=[],busy=false;
function mode(on){$("#test-mode").disabled=on;$("#test-mode").textContent=on?"テスト中・保存なし":"テストモード";}
$("#test-mode").onclick=async()=>{try{mode((await api("test")).test);}catch(e){bubble(e.message);}};
function show(){const active=!!token;$("#welcome").hidden=active;$("#thread").hidden=!active;$("#lock").hidden=!active;}
function clear(){token="";history=[];sessionStorage.removeItem("ippatsu.chat.lastReceipt");sessionStorage.removeItem("ippatsu.chat.history");sessionStorage.removeItem("ippatsu.chat.session");sessionStorage.removeItem("ippatsu.chat.pending");$("#messages").replaceChildren();show();}
async function api(action,data={}){
  let response;
  try{response=await fetch(endpoint,{method:"POST",headers:{"Content-Type":"application/json",...(token?{"x-ippatsu-session":token}:{})},body:JSON.stringify({action,...data}),cache:"no-store"});}
  catch{throw Error("通信できません。電波のよい場所で結果を確認してください。");}
  const result=await response.json();
  if(!response.ok){if(response.status===401&&token){clear();$("#notice").textContent="暗証番号をもう一度入力してください。";}throw Error(result.message||"処理できませんでした。");}
  return result;
}
function bubble(text,mine=false,citations=[],sticker=null){const row=document.createElement("div");row.className=mine?"row mine":"row";
  if(!mine){const img=document.createElement("img");img.src="ippatsu.webp";img.alt="いっぱつちゃん";row.append(img);}
  const box=document.createElement("div");box.className="bubble";box.textContent=text;
  if(!mine && citations.length){
    box.replaceChildren();let offset=0;
    for(const c of citations){
      if(!Number.isInteger(c.start)||!Number.isInteger(c.end)||c.start<offset||c.end<c.start||c.end>text.length||!/^https?:\/\//i.test(c.url))continue;
      const span=text.slice(c.start,c.end);
      box.append(text.slice(offset,c.start));
      const a=document.createElement("a");a.href=c.url;a.target="_blank";a.rel="noopener noreferrer";
      a.textContent=span && !/https?:|【|/.test(span)?span:"〔"+new URL(c.url).hostname+"〕";
      a.title=c.title||"";box.append(a);offset=c.end;
    }
    box.append(text.slice(offset));
  }
  const file=!mine && ({salute:"salute.webp",thanks:"thanks.webp"})[sticker];
  if(typeof file==="string"){const art=document.createElement("img");art.src=file;art.alt="";art.className="sticker";box.append(art);}
  row.append(box);
  const messages=$("#messages");messages.append(row);messages.scrollTop=messages.scrollHeight;return box;}
function saveHistory(){
  history=history.slice(-24);
  try{sessionStorage.setItem("ippatsu.chat.history",JSON.stringify({date:new Date().toLocaleDateString("ja-JP",{timeZone:"Asia/Tokyo"}),messages:history}));}catch{}
}
function pending(id,text){sessionStorage.setItem("ippatsu.chat.lastReceipt",id);sessionStorage.setItem("ippatsu.chat.pending",JSON.stringify({id,text}));}
function confirmation(id,text,check=false){
  const box=bubble(text),button=document.createElement("button");button.type="button";button.className="apply";box.append(button);
  button.textContent=check?"結果を読み直す":"この内容で反映";
  let timer, receipt, lastMessage;
  button.onclick=async()=>{
    clearTimeout(timer);
    button.disabled=true;
    try{const r=await api(check?"status":"apply",{id});
      if(r.state==="preview"){if(check){confirmation(id,r.summary);button.remove();return;}}
      const message=r.message||r.summary;
      // Saving the completion event and publishing its archive are separate receipts.
      const publicationPending=r.state==="saved" && text.includes("の完了報告") && !message.includes("予定を終了しました");
      if(!receipt || message!==lastMessage){
        if(receipt)receipt.textContent=message;
        else receipt=bubble(message);
        if(lastMessage && history.at(-1)?.content===lastMessage.slice(0,1800))history.pop();
        history.push({role:"assistant",content:message.slice(0,1800)});
        saveHistory();
        lastMessage=message;
      }
      if(r.state==="saved" && !publicationPending){
        const art=document.createElement("img");
        art.src="done.webp";art.alt="DB保存完了っす！";art.className="sticker";
        receipt.append(document.createElement("br"),document.createTextNode("DB保存完了っす！"),art);
      }
      if(r.state==="queued"||r.state==="running"||publicationPending){
        check=publicationPending||!r.awaiting_dispatch;
        button.textContent=check?"進捗を確認":"クラウド処理を開始";
        if(check)timer=setTimeout(()=>{if(button.isConnected&&!button.disabled)button.click();},15000);
      }
      else{button.remove();sessionStorage.removeItem("ippatsu.chat.pending");}
    }catch(e){bubble(e.message);check=true;button.textContent="受付結果を確認";}finally{button.disabled=false;}
  };
}
function start(){show();if(!token)return;api("mode").then(r=>mode(r.test)).catch(e=>bubble(e.message));
  try {
    const saved=JSON.parse(sessionStorage.getItem("ippatsu.chat.history") || "null");
    if(saved?.date===new Date().toLocaleDateString("ja-JP",{timeZone:"Asia/Tokyo"}) && Array.isArray(saved.messages)){
      history=saved.messages.slice(-24);
      for(const msg of history)bubble(msg.content,msg.role==="user",msg.citations,msg.sticker);
    }
  }catch{}
  if(!history.length)bubble("おつかれさまっす！ 今日の予定、確認しましょうか？");
  try{const p=JSON.parse(sessionStorage.getItem("ippatsu.chat.pending"));if(p)confirmation(p.id,p.text,true);}catch{}}
$("#login").onsubmit=async e=>{e.preventDefault();const b=$("#login button");b.disabled=true;$("#notice").textContent="";
  try{const r=await api("login",{pin:$("#pin").value});token=r.token;sessionStorage.setItem("ippatsu.chat.session",token);$("#pin").value="";start();}
  catch(e){$("#notice").textContent=e.message;}finally{b.disabled=false;}};
$("#lock").onclick=async()=>{try{await api("logout");}finally{clear();}};
async function send(text){if(!text||busy)return;busy=true;$("#compose button").disabled=true;$("#typing").hidden=false;
  bubble(text,true);history.push({role:"user",content:text});$("#message").value="";
  const messages=history.slice(-25).map(({role,content})=>({role,content}));
  while(messages.length>1 && JSON.stringify(messages).length>24000)messages.shift();
  try{const r=await api("chat",{messages,receiptId:sessionStorage.getItem("ippatsu.chat.lastReceipt")});
    mode(r.test);
    history.push({role:"assistant",content:r.message.slice(0,1800),citations:r.citations,sticker:r.sticker});
    saveHistory();
    if(r.proposal){pending(r.proposal,r.message);confirmation(r.proposal,r.message);}else{
      const box=bubble(r.message,false,r.citations,r.sticker);
      if(r.cancelReport)cancelButton(box,r.cancelReport);
      for(const item of r.links||[]){const url=new URL(item.url);
        if(url.origin!==location.origin||!url.pathname.startsWith("/ippatsu-share-pages/"))continue;
        const a=document.createElement("a");a.href=url.href;a.textContent=item.label;a.className="result-link";box.append(a);}
    }
  }catch(e){bubble(e.message);}finally{busy=false;$("#compose button").disabled=false;$("#typing").hidden=true;}}
$("#compose").onsubmit=e=>{e.preventDefault();send($("#message").value.trim());};
$("#message").onkeydown=e=>{if(e.key==="Enter"&&(e.ctrlKey||e.metaKey)&&!e.isComposing){e.preventDefault();send($("#message").value.trim());}};
$("#reset").onclick=async()=>{
  if(busy||$("#messages button:disabled")){bubble("処理中っす。応答が届いてから会話を切り替えてください。");return;}
  if(!confirm("新しい会話にしますか？ 入力中の文と確認待ちの表示を消します。すでに受け付けた処理は受付履歴で確認できます。"))return;
  try{const r=await api("reset");token=r.token;sessionStorage.setItem("ippatsu.chat.session",token);}catch(e){bubble(e.message);return;}
  history=[];
  sessionStorage.removeItem("ippatsu.chat.lastReceipt");sessionStorage.removeItem("ippatsu.chat.history");
  sessionStorage.removeItem("ippatsu.chat.pending");
  $("#message").value="";
  $("#messages").replaceChildren();
  start();
};
function cancelButton(box,report){
    const button=document.createElement("button");
    button.textContent="この未起動の受付を取り消す";box.append(button);
    button.onclick=async()=>{
      if(!confirm(report.summary+"\nこの受付を取り消しますか？"))return;
      button.disabled=true;
      try{const result=await api("cancel",{id:report.id});bubble(result.message);}
      catch(e){bubble(e.message);button.disabled=false;}
    };
}
$("#recent").onclick=async()=>{try{
  const recent=await api("recent");bubble(recent.message);
  for(const report of recent.pending||[]){
    cancelButton(bubble(report.summary),report);
  }
}catch(e){bubble(e.message);}};
document.querySelectorAll(".suggestions button:not(#recent):not(#reset):not(#test-mode)").forEach(b=>b.onclick=()=>send(b.textContent));start();

