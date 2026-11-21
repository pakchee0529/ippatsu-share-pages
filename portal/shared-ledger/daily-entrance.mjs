const endpoint='https://evmgsqdrojxppxknrzfk.supabase.co/functions/v1/field-entrance';
const viewer=new URL('../sandbox/entrance/',import.meta.url);
const normalize=value=>String(value??'').normalize('NFKC').toLowerCase().replace(/\s+/gu,'').replace(/[〜～]/gu,'~');
function identity(number,label){
  const a=normalize(number), b=normalize(label);
  return a && b ? JSON.stringify([a,b]) : '';
}
export function attachEntranceLinks(date){
  if (!/^\d{6}$/.test(date) || !location.pathname.match(new RegExp('/share/'+date+'/(?:index\\.html)?$'))) return;
  const cards=new Map();
  for (const card of document.querySelectorAll('article.card[data-date]')) {
    if (card.dataset.date!==date) continue;
    const key=identity(card.dataset.managementNoKey,card.querySelector('.card-title')?.textContent);
    if(key) cards.set(key,cards.has(key)?null:card);
  }
  if(!cards.size)return;
  let generation=0;
  async function refresh(){
    const version=++generation;
    try{
      const response=await fetch(endpoint,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({action:'dailyAvailability',date}),signal:AbortSignal.timeout(12000)});
      if(!response.ok)throw Error();
      const {items}=await response.json();
      if(version!==generation)return;
      const matches=new Map();
      for(const item of items){
        const key=identity(item.management_no,item.label);
        matches.set(key,matches.has(key)?null:item);
      }
      for(const [key,card] of cards){
        if(!card)continue;
        const item=matches.get(key);
        let link=card.querySelector('[data-entrance-link]');
        if(!item || !(item.photo_count>0) || !/^[\da-f]{8}(?:-[\da-f]{4}){3}-[\da-f]{12}$/i.test(item.case_id)){link?.remove();continue;}
        if(!link){
          link=document.createElement('a');link.className='btn btn-note';link.dataset.entranceLink='';
          link.textContent='進入路を見る';card.querySelector('.card-actions')?.append(link);
        }
        const url=new URL(viewer);url.search=new URLSearchParams({mode:'view',case_id:item.case_id});link.href=url.href;
      }
    } catch {
      if(version===generation) for(const card of cards.values())card?.querySelector('[data-entrance-link]')?.remove();
    }
  }
  refresh();
  document.addEventListener('visibilitychange',()=>{if(!document.hidden)refresh()});
  addEventListener('pageshow',event=>{if(event.persisted)refresh()});
}
