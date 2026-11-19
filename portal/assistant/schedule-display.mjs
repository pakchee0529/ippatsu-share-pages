// Shared display contains only the publishable span titles and their current order.
const view=document.getElementById("assistant-schedule");
const content=document.getElementById("assistant-schedule-days");
async function refresh(){
  try{
    const response=await fetch("https://evmgsqdrojxppxknrzfk.supabase.co/functions/v1/ippatsu-assistant?view=schedule",{cache:"no-cache"});
    if(!response.ok)throw Error();
    const days=await response.json();
    const nodes=[];
    for(const {day,titles} of days){
      if(!/^\d{6}$/.test(day)||!Array.isArray(titles))throw Error();
      const detail=document.createElement("details"),summary=document.createElement("summary");
      summary.textContent=Number(day.slice(2,4))+"月"+Number(day.slice(4,6))+"日　"+titles.length+"件";
      detail.append(summary);
      const list=document.createElement("ol");
      for(const title of titles){const li=document.createElement("li");li.textContent=title;list.append(li);}
      detail.append(list);nodes.push(detail);
    }
    content.replaceChildren(...nodes);view.hidden=!nodes.length;
  }catch{if(!view.hidden)content.textContent="最新の予定を取得できません。ページを開き直してください。";}
}
refresh();window.addEventListener("pageshow",e=>{if(e.persisted)refresh();});
document.addEventListener("visibilitychange",()=>{if(!document.hidden)refresh();});

