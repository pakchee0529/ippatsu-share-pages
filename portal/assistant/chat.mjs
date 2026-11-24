import {numberedChoices,resolveChoice} from './choices.mjs';
import {workingStatus} from './working.mjs';
import {openAccount,forget,rotate} from '../account/session.mjs';
const $=s=>document.querySelector(s);
// Bind a day only when the user opens its dedicated chat entry.
function selectedPageDate(search){
  const values=new URLSearchParams(search).getAll("date");
  if(values.length!==1 || !/^\d{6}$/.test(values[0]))return null;
  const day=values[0],iso="20"+day.slice(0,2)+"-"+day.slice(2,4)+"-"+day.slice(4);
  const stamp=Date.parse(iso+"T00:00:00Z");
  return Number.isFinite(stamp) && new Date(stamp).toISOString().slice(0,10)===iso ? iso : null;
}
const pageDate=selectedPageDate(location.search);
function conversationKey(name){
  return "ippatsu.chat."+name+(pageDate?"."+pageDate:"");
}
if(pageDate){
  const day=pageDate.slice(2).replaceAll("-","");
  const back=$("header .back");
  back.href="../../share/"+day+"/";
  back.setAttribute("aria-label","この日の現場へ戻る");
  $("header h1 + p").textContent=Number(day.slice(2,4))+"月"+Number(day.slice(4))+"日の現場";
}
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
function show(){const active=!!token;$("#welcome").hidden=active;$("#thread").hidden=!active;$("#usage").hidden=!active;if(!active){$("#usage").open=false;$("#balance-label").textContent="残量 —";}}
function clear(){forget();resetInputMode();token="";history=[];sessionStorage.removeItem(conversationKey("lastReceipt"));sessionStorage.removeItem(conversationKey("history"));sessionStorage.removeItem("ippatsu.chat.session");sessionStorage.removeItem(conversationKey("pending"));$("#messages").replaceChildren();show();}
async function api(action,data={}){
  let response;
  try{response=await fetch(endpoint,{method:"POST",headers:{"Content-Type":"application/json",...(token?{"x-ippatsu-session":token}:{})},body:JSON.stringify({action,...data}),cache:"no-store"});}
  catch{throw Error("通信できません。電波のよい場所で結果を確認してください。");}
  const result=await response.json();
  if(!response.ok){if(response.status===401&&token){clear();$("#notice").textContent="暗証番号をもう一度入力してください。";}throw Error(result.message||"処理できませんでした。");}
  return result;
}
function bubble(text,mine=false,citations=[],sticker=null,links=[],poleCards=[]){const row=document.createElement("div");row.className=mine?"row mine":"row";
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
  if(!mine){
    for(const node of [...box.childNodes]){
      if(node.nodeType!==Node.TEXT_NODE || !node.data.includes("**"))continue;
      const parts=document.createDocumentFragment();let start=0;
      for(const match of node.data.matchAll(/\*\*([^*\n]+?)\*\*/g)){
        parts.append(node.data.slice(start,match.index));
        const strong=document.createElement("strong");strong.textContent=match[1];parts.append(strong);
        start=match.index+match[0].length;
      }
      if(start){parts.append(node.data.slice(start));node.replaceWith(parts);}
    }
  }
  const file=!mine && ({salute:"salute.webp",thanks:"thanks.webp"})[sticker];
  if(typeof file==="string"){const art=document.createElement("img");art.src=file;art.alt="";art.className="sticker";box.append(art);}
  row.append(box);
  for(const item of links){
    if(typeof item?.url!=="string" || !URL.canParse(item.url))continue;
    const url=new URL(item.url);
    const portal=url.origin===location.origin && url.pathname.startsWith("/ippatsu-share-pages/");
    const map=/^https:\/\/www\.google\.com\/maps\?q=-?\d+(?:\.\d+)?,-?\d+(?:\.\d+)?$/.test(url.href);
    if(!portal&&!map)continue;
    const a=document.createElement("a");a.href=url.href;a.textContent=item.label;a.className="result-link";
    if(map){a.target="_blank";a.rel="noopener noreferrer";}
    box.append(a);
  }
  if(!mine && poleCards.length){
    box.replaceChildren();
    for(const card of poleCards)box.append(poleCard(card));
  }
  const messages=$("#messages");messages.append(row);messages.scrollTop=messages.scrollHeight;return box;}
function poleCard(card){
  const section=document.createElement("section");section.className="pole-result";
  const linksOnly=$("#pole-links-only").checked;
  const title=document.createElement("strong");title.textContent=card.title;section.append(title);
  const notes=[...(card.rows||[]).map(r=>r.label+"　"+r.value),...(card.notes||[]),...(card.warnings||[])];
  if(card.status==="unresolved")notes.unshift("電柱を特定できませんでした。");
  if(card.status==="partial")notes.unshift("片側のみ特定できました。");
  if(!linksOnly || !card.primary_url || card.status==="partial" || card.status==="corrected")
    for(const note of notes){const p=document.createElement("p");p.textContent=note;section.append(p);}
  const bot="https://line-map-bot-ouvo.onrender.com";
  for(const [value,label] of [[card.primary_url,card.primary_label],[card.secondary_url,card.secondary_label]]){
    if(!value||!URL.canParse(value))continue;
    const url=new URL(value);
    if(!(url.origin===bot && ["/map","/multi-map"].includes(url.pathname)) &&
       !(url.origin==="https://www.google.com" && url.pathname==="/maps"))continue;
    const a=document.createElement("a");a.className="result-link";a.href=url.href;a.textContent=label||"地図を開く";
    a.target="_blank";a.rel="noopener noreferrer";section.append(a);
  }
  if(!linksOnly && card.preview_url && URL.canParse(card.preview_url)){
    const url=new URL(card.preview_url);
    if(url.origin===bot && url.pathname==="/api/map-preview"){
      const img=document.createElement("img");img.loading="lazy";img.alt="地図プレビュー";img.src=url.href;section.append(img);
    }
  }
  for(const name of card.candidates||[]){
    const b=document.createElement("button");b.type="button";b.textContent=name;b.onclick=()=>send(name,"poleSearch");section.append(b);
  }
  return section;
}
function saveHistory(){
  history=history.slice(-24);
  try{sessionStorage.setItem(conversationKey("history"),JSON.stringify({date:new Date().toLocaleDateString("ja-JP",{timeZone:"Asia/Tokyo"}),messages:history}));}catch{}
}
function pending(id,text){sessionStorage.setItem(conversationKey("lastReceipt"),id);sessionStorage.setItem(conversationKey("pending"),JSON.stringify({id,text}));}
function confirmation(id,text,check=false){
  const box=bubble(text),button=document.createElement("button");button.type="button";button.className="apply";box.append(button);
  button.textContent=check?"結果を読み直す":"この内容で反映";
  let timer, receipt, lastMessage;
  button.onclick=async()=>{
    clearTimeout(timer);
    button.disabled=true;
    try{const r=await api(check?"status":"apply",{id});
      if(r.state==="preview"){if(check){confirmation(id,r.summary);button.remove();return;}}
      const schedule=r.workflow_kind==="schedule";
      const message=r.message||r.summary||"受付の状態を確認してください。";
      // Saving the completion event and publishing its archive are separate receipts.
      const publicationPending=!schedule && r.state==="saved" && text.includes("の完了報告") && !message.includes("予定を終了しました");
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
        art.src="done.webp";art.alt="";art.className="sticker";
        const done=schedule?"共有ページまで反映できたっす！":"DB保存完了っす！";
        receipt.append(document.createElement("br"),document.createTextNode(done),art);
        if(schedule && r.publication==="published" && Array.isArray(r.published_days)){
          for(const day of new Set(r.published_days)){
            if(typeof day!=="string" || !/^\d{6}$/.test(day))continue;
            const link=document.createElement("a");
            link.href="../../share/"+day+"/";
            link.className="result-link";
            link.textContent=Number(day.slice(2,4))+"月"+Number(day.slice(4))+"日の現場を開く";
            receipt.append(link);
          }
        }
      }
      if(r.state==="queued"||r.state==="running"||publicationPending){
        check=schedule||publicationPending||!r.awaiting_dispatch;
        button.textContent=schedule?"共有ページの反映状況を確認":check?"進捗を確認":"クラウド処理を開始";
        if(check)timer=setTimeout(()=>{if(button.isConnected&&!button.disabled)button.click();},15000);
      }
      else if(schedule && r.state==="held"){
        check=false;
        button.textContent="この受付の公開処理を再開";
      }else{
        button.remove();
        const active=JSON.parse(sessionStorage.getItem(conversationKey("pending"))||"null");
        if(active?.id===id)sessionStorage.removeItem(conversationKey("pending"));
      }
    }catch(e){bubble(e.message);check=true;button.textContent="受付結果を確認";}finally{button.disabled=false;}
  };
}
let balanceRequest=null, balanceTime=0;
async function refreshBalance(){
  if(!token || document.hidden || balanceRequest===token || Date.now()-balanceTime<300000)return;
  const session=token;
  balanceRequest=session;
  try{
    const r=await api("monthlyBalance");
    if(session!==token)return;
    if(!r.available)throw Error();
    $("#balance-label").textContent="残り約"+r.remaining+"%";
    const time=new Intl.DateTimeFormat("ja-JP",{timeZone:"Asia/Tokyo",month:"numeric",day:"numeric",hour:"2-digit",minute:"2-digit"}).format(r.checked);
    $("#balance-detail").textContent="無料枠 $100 ／ 推定残額 $"+Math.max(0,r.budget-r.used).toFixed(2)+"。有効期限 "+r.next.slice(0,10).replaceAll("-","/")+"。"+time+" 集計";
    balanceTime=Date.now();
  }catch{if(session===token){$("#balance-label").textContent="残量 —";$("#balance-detail").textContent="無料枠の残量を確認できませんでした。";}}
  finally{if(balanceRequest===session)balanceRequest=null;}
}
$("#usage").addEventListener("toggle",()=>{if($("#usage").open)refreshBalance();});
document.addEventListener("visibilitychange",refreshBalance);
setInterval(refreshBalance,300000);
function start(){show();if(!token)return;balanceTime=0;refreshBalance();api("mode").then(r=>mode(r.test)).catch(e=>bubble(e.message));
  try {
    const saved=JSON.parse(sessionStorage.getItem(conversationKey("history")) || "null");
    if(saved?.date===new Date().toLocaleDateString("ja-JP",{timeZone:"Asia/Tokyo"}) && Array.isArray(saved.messages)){
      history=saved.messages.slice(-24);
      for(const msg of history)bubble(msg.content,msg.role==="user",msg.citations,msg.sticker,msg.links,msg.poleCards);
    }
  }catch{}
  if(!history.length)bubble(pageDate?"おつかれさまっす！ この日の現場、何を確認しましょうか？":"おつかれさまっす！ 今日の予定、確認しましょうか？");
  try{const p=JSON.parse(sessionStorage.getItem(conversationKey("pending")));if(p)confirmation(p.id,p.text,true);}catch{}}
$("#account-entry").onclick=()=>openAccount(()=>location.reload());
$("#login").onsubmit=async e=>{e.preventDefault();const b=$("#login button");b.disabled=true;$("#notice").textContent="";
  try{const r=await api("login",{pin:$("#pin").value});token=r.token;sessionStorage.setItem("ippatsu.chat.session",token);$("#pin").value="";start();}
  catch(e){$("#notice").textContent=e.message;}finally{b.disabled=false;}};
$("#lock").onclick=async()=>{try{await api("logout");}finally{clear();}};
const chatWork=workingStatus(document.querySelector('#typing'));
// The schedule planner resolves a numbered nearby case against its own dated list.
function nearbyCaseChoices(mode,message){
  return mode==="chat" && message.startsWith("近くの追加候補　");
}
async function send(text,action="chat",query=text){if(!text||busy)return;busy=true;$("#compose button").disabled=true;$("#typing").hidden=false;chatWork.show(action==="poleSearch"?"電柱を探しています":"返事を準備しています");
  const last=history.findLast(turn=>!turn.mode||turn.mode===action);
  const choices=last?.role==="assistant" && last.mode===action && !nearbyCaseChoices(action,last.content) ? last.choices || [] : [];
  const selection=query===text && resolveChoice(text,choices);
  bubble(text,true);history.push({role:"user",mode:action,content:text});
  if(selection?.question){
    bubble(selection.question);history.push({role:"assistant",mode:action,content:selection.question,choices});saveHistory();
    busy=false;$("#compose button").disabled=false;chatWork.clear();$("#typing").hidden=true;return;
  }
  if(selection?.value){query=selection.value;history.at(-1).resolved=query;}
  const turns=history.filter(turn=>!turn.mode||turn.mode===action);
  const messages=turns.slice(-25).map(({role,content,choices,resolved})=>({role,content:resolved?content+"（選択："+resolved+"）":role==="assistant"&&choices?.length&&!numberedChoices(content).length?content+"\n"+choices.map((v,i)=>(i+1)+". "+v).join("\n"):content}));
  if(selection?.value)messages.at(-1).content=text+"（直前の候補「"+selection.value+"」）";
  for(const message of messages)message.content=message.content.slice(0,1800);
  while(messages.length>1 && JSON.stringify(messages).length>24000)messages.shift();
  try{const r=action==="poleSearch"?await api(action,{query}):await api("chat",{messages,...(pageDate?{pageDate}:{}),searchRef:last?.searchRef,receiptId:sessionStorage.getItem(conversationKey("lastReceipt"))});
    mode(r.test);
    const candidates=(r.poleCards||[]).flatMap(card=>card.candidates||[]);
    history.push({role:"assistant",mode:action,choices:nearbyCaseChoices(action,r.message)?[]:candidates.length?candidates:numberedChoices(r.message),content:r.message.slice(0,1800),citations:r.citations,sticker:r.sticker,links:r.links,searchRef:r.searchRef,poleCards:r.poleCards});
    saveHistory();
    if(r.proposal){pending(r.proposal,r.message);confirmation(r.proposal,r.message);}else{
      const box=bubble(r.message,false,r.citations,r.sticker,r.links,r.poleCards);
      if(r.cancelReport)cancelButton(box,r.cancelReport);

    }
  }catch(e){bubble(e.message);}finally{busy=false;$("#compose button").disabled=false;chatWork.clear();$("#typing").hidden=true;}}
$("#compose").onsubmit=e=>{
  e.preventDefault();
  const field=$("#message"),text=field.value.trim();
  if(!text || busy)return;
  field.value="";
  send(text,searchMode?"poleSearch":"chat");
};
$("#message").onkeydown=e=>{if(e.key==="Enter"&&(e.ctrlKey||e.metaKey)&&!e.isComposing){e.preventDefault();$("#compose").requestSubmit();}};
$("#reset").onclick=async()=>{
  if(busy||$("#messages button:disabled")){bubble("処理中っす。応答が届いてから会話を切り替えてください。");return;}
  if(!confirm("新しい会話にしますか？ 入力中の文と確認待ちの表示を消します。すでに受け付けた処理は受付履歴で確認できます。"))return;
  try{const r=await api("reset");token=r.token;rotate(token);sessionStorage.setItem("ippatsu.chat.session",token);}catch(e){bubble(e.message);return;}
  history=[];
  sessionStorage.removeItem(conversationKey("lastReceipt"));sessionStorage.removeItem(conversationKey("history"));
  sessionStorage.removeItem(conversationKey("pending"));
  resetInputMode();
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
let searchMode=false,locationRequest=0;
const drafts={chat:"",search:""};
function locationNotice(text){
  $("#pole-notice").textContent=text;
  $("#pole-notice").hidden=!text;
}
let sandboxMode=false;
function setInputMode(search,sandbox=false){
  const field=$("#message");
  if(!sandboxMode)drafts[searchMode?"search":"chat"]=field.value;
  sandboxMode=sandbox;
  searchMode=search;
  sessionStorage.setItem("ippatsu.chat.inputMode",sandbox?"sandbox":search?"search":"chat");
  field.value=drafts[search?"search":"chat"];
  field.placeholder=search?"電柱名・径間名・座標（複数は改行）":"メッセージを書く";
  field.setAttribute("aria-label",search?"電柱検索の入力":"メッセージ");
  field.rows=search?2:1;
  const submit=$("#compose button");
  submit.textContent=search?"検索":"送信";
  submit.setAttribute("aria-label",submit.textContent);
  $("#chat-mode").setAttribute("aria-pressed",String(!search&&!sandbox));
  $("#pole-mode").setAttribute("aria-pressed",String(search));
  $("#sandbox-mode").setAttribute("aria-pressed",String(sandbox));
  $("#sandbox-tools").hidden=!sandbox;
  $("#messages").hidden=sandbox;
  $("#compose").hidden=sandbox;
  $("#chat-tools").hidden=search||sandbox;
  $("#pole-tools").hidden=!search;
  locationRequest++;
  $("#pole-geo").disabled=false;
  locationNotice("");
}
function resetInputMode(){
  drafts.chat=drafts.search="";
  $("#message").value="";
  setInputMode(false);
}
$("#sandbox-mode").onclick=()=>setInputMode(false,true);
$("#chat-mode").onclick=()=>setInputMode(false);
$("#pole-mode").onclick=()=>setInputMode(true);
$("#pole-links-only").checked=localStorage.getItem("ippatsu.pole.linksOnly")==="true";
$("#pole-links-only").onchange=e=>localStorage.setItem("ippatsu.pole.linksOnly",String(e.target.checked));
$("#pole-geo").onclick=()=>{
  if(busy){locationNotice("検索結果が届いてからもう一度押してください。");return;}
  if(!navigator.geolocation){locationNotice("この端末では現在地を取得できません。座標を入力してください。");return;}
  const current=++locationRequest;
  $("#pole-geo").disabled=true;locationNotice("現在地を確認中…");
  navigator.geolocation.getCurrentPosition(pos=>{
    if(current!==locationRequest)return;
    $("#pole-geo").disabled=false;
    if(busy){locationNotice("検索結果が届いてからもう一度押してください。");return;}
    locationNotice("");
    send("現在地の周辺200mの電柱","poleSearch",pos.coords.latitude.toFixed(6)+","+pos.coords.longitude.toFixed(6));
  },()=>{
    if(current!==locationRequest)return;
    $("#pole-geo").disabled=false;
    locationNotice("現在地を取得できません。位置情報の許可を確認するか座標を入力してください。");
  },{enableHighAccuracy:true,timeout:15000,maximumAge:30000});
};
document.querySelectorAll("[data-chat]").forEach(b=>b.onclick=()=>send(b.textContent));
const restoredMode=new URLSearchParams(location.search).get("mode")==="sandbox"?"sandbox":token && sessionStorage.getItem("ippatsu.chat.inputMode");
setInputMode(restoredMode==="search",restoredMode==="sandbox");
start();

