const areaIds = {五條:'gojo',大塔:'oto',十津川:'totsukawa',吉野:'yoshino',大淀:'oyodo'};
const endpoint = 'https://evmgsqdrojxppxknrzfk.supabase.co/functions/v1/field-weather';
const hourMs=3600000, cacheMs=600000;
const mounted=new WeakMap();
const timezone='Asia/Tokyo';
const timeLabel=new Intl.DateTimeFormat('ja-JP',{timeZone:timezone,hourCycle:'h23',hour:'numeric'});
const dateLabel=new Intl.DateTimeFormat('ja-JP',{timeZone:timezone,month:'numeric',day:'numeric'});
const stampLabel=new Intl.DateTimeFormat('ja-JP',{timeZone:timezone,hourCycle:'h23',month:'numeric',day:'numeric',hour:'2-digit',minute:'2-digit'});
const numberLabel=new Intl.NumberFormat('ja-JP',{maximumFractionDigits:1});
const timestamp=value=>typeof value==='string'&&Number.isFinite(Date.parse(value))?Date.parse(value):null;
const hourNumber=ms=>Number(timeLabel.formatToParts(ms).find(part=>part.type==='hour').value);
const formatValue=(value,unit)=>typeof value==='number'&&Number.isFinite(value)?numberLabel.format(value)+unit:'—';
function node(tag,cls,content){
  const item=document.createElement(tag);
  if(cls)item.className=cls;
  if(content!==undefined)item.textContent=content;
  return item;
}
function describe(symbol){
  const code=String(symbol||'').toLowerCase(),night=code.endsWith('_night');
  if(code.includes('thunder'))return {label:code.includes('snow')?'雪・雷':code.includes('sleet')?'みぞれ・雷':'雨・雷',icon:'thunder'};
  if(code.includes('sleet'))return {label:'みぞれ',icon:'sleet'};
  if(code.includes('snow'))return {label:code.startsWith('heavy')?'強い雪':code.startsWith('light')?'小雪':'雪',icon:'snow'};
  if(code.includes('rain'))return {label:code.startsWith('heavy')?'強い雨':code.startsWith('light')?'小雨':code.includes('showers')?'にわか雨':'雨',icon:'rain'};
  if(code.startsWith('partlycloudy'))return {label:'晴れ時々曇り',icon:night?'nightcloud':'suncloud'};
  if(code.startsWith('fair'))return {label:'おおむね晴れ',icon:night?'nightcloud':'suncloud'};
  if(code.startsWith('clearsky'))return {label:'晴れ',icon:night?'moon':'sun'};
  if(code.startsWith('cloudy'))return {label:'曇り',icon:'cloud'};
  if(code.startsWith('fog'))return {label:'霧',icon:'fog'};
  return {label:'—',icon:'unknown'};
}
function glyph(type){
  const g=document.createElementNS('http://www.w3.org/2000/svg','svg');
  g.setAttribute('viewBox','0 0 40 36');g.setAttribute('aria-hidden','true');g.classList.add('wx-symbol');
  function shape(tag,attrs){
    const el=document.createElementNS(g.namespaceURI,tag);
    for(const [key,value] of Object.entries(attrs))el.setAttribute(key,value);
    g.append(el);
  }
  function path(d,cls){shape('path',{d,class:cls});}
  if(type==='unknown'){path('M14 18h12','wx-muted-line');return g;}
  const combined=type==='suncloud'||type==='nightcloud';
  if(type==='sun'||type==='suncloud'){
    const x=combined?14:20,y=combined?12:18,r=combined?5:7;
    shape('circle',{cx:x,cy:y,r,class:'wx-sun'});
    for(let i=0;i<8;i++){
      const a=i*Math.PI/4,cos=Math.cos(a),sin=Math.sin(a);
      path(`M${x+(r+3)*cos} ${y+(r+3)*sin}l${cos*2.4} ${sin*2.4}`,'wx-sun-ray');
    }
  }
  if(type==='moon'||type==='nightcloud')path(combined?'M16 4a9 9 0 1 0 8 12A9 9 0 0 1 16 4Z':'M22 4a14 14 0 1 0 10 22A15 15 0 0 1 22 4Z','wx-moon');
  if(!['moon','sun'].includes(type))path('M10 24a6 6 0 0 1-1-12 9 9 0 0 1 16-3 6 6 0 0 1 8 5 5 5 0 0 1-1 10Z','wx-cloud');
  if(type==='thunder')path('m21 20-5 8h5l-2 6 9-11h-6l3-3Z','wx-bolt');
  if(type==='rain'||type==='sleet')path('m13 27-2 4m10-4-2 4m10-4-2 4','wx-rain');
  if(type==='snow'||type==='sleet')for(const x of (type==='snow'?[12,20,28]:[16,25]))shape('circle',{cx:x,cy:type==='snow'?29:33,r:1.6,class:'wx-snow'});
  if(type==='fog')path('M5 27h25m-20 5h25','wx-muted-line');
  return g;
}
function periodLabel(hour){
  const start=timestamp(hour.pop_period_start),end=timestamp(hour.pop_period_end);
  if(start===null||end===null||end<=start)return '';
  if(end-start===hourMs)return '1時間';
  return hourNumber(start)+'–'+(hourNumber(end)===0&&end-start<24*hourMs?24:hourNumber(end))+'時';
}
function cell(cls,value,description){
  const el=node('span',cls,value);
  el.setAttribute('aria-label',description+' '+(value==='—'?'データなし':value));
  return el;
}
function paint(target,data,area){
  const scope=node('p','wx-location',data.point_label||area);
  const rail=node('div','wx-rail'),key=node('div','wx-key');
  key.setAttribute('aria-hidden','true');
  for(const [cls,text] of [['wx-time','時刻'],['wx-art',''],['wx-condition','天気'],['wx-temp','気温'],['wx-pop','降水確率'],['wx-span','対象時間'],['wx-mm','1時間雨量']])key.append(node('span',cls,text));
  const strip=node('ol','wx-hours');strip.tabIndex=0;strip.setAttribute('aria-label','日本時間の時間別予報。横にスクロールできます。');
  let lastDay;
  for(const hour of data.hours){
    const at=timestamp(hour.time);if(at===null)continue;
    const day=dateLabel.format(at),clock=hourNumber(at)+'時',c=describe(hour.symbol);
    const item=node('li','wx-hour');
    const time=node('time','wx-time',clock);time.dateTime=hour.time;
    const dayTag=node('small','wx-date',day!==lastDay?day:'');
    time.prepend(dayTag);time.setAttribute('aria-label',day+' '+clock+' 日本時間');lastDay=day;
    const art=node('span','wx-art');art.append(glyph(c.icon));
    const condition=cell('wx-condition',c.label,'天気');
    const temp=cell('wx-temp',formatValue(hour.temp_c,'℃'),'気温');
    const pop=cell('wx-pop',formatValue(hour.pop,'%'),'降水確率');
    const period=cell('wx-span',hour.pop==null?'—':periodLabel(hour)||'—','降水確率の対象時間');
    if(typeof hour.pop_source==='string')period.title=hour.pop_source;
    const mm=cell('wx-mm',formatValue(hour.precip_mm,' mm'),'この時刻から1時間の予想降水量');
    item.append(time,art,condition,temp,pop,period,mm);strip.append(item);
  }
  if(!strip.children.length)throw Error('時間別予報がありません。');
  rail.append(key,strip);
  const source=node('p','wx-source');
  const metAt=timestamp(data.updated_at);
  if(metAt!==null)source.append('　予報更新 '+stampLabel.format(metAt));
  if(data.hours.some(h=>h.pop_source==='気象庁'&&h.pop!=null)){
    const jma=node('span','wx-jma');
    jma.textContent=(data.jma_area||area)+'の6時間降水確率';
    const issued=timestamp(data.jma_updated_at);
    if(issued!==null)jma.append('　発表 '+stampLabel.format(issued));
    source.append(jma);
  }
  const old=target.querySelector('.wx-hours')?.scrollLeft||0;
  target.replaceChildren(scope,rail,source);strip.scrollLeft=old;
}

export function mountWeather(container,area){
  mounted.get(container)?.();
  const id=areaIds[area];if(!id)throw Error('天気を表示できない地域です。');
  const root=node('section','wx-forecast'),header=node('div','wx-heading');
  const heading=node('h3','','これから12時間の予報');
  const refresh=node('button','wx-refresh','更新');refresh.type='button';refresh.setAttribute('aria-label',area+'の予報を更新');
  const status=node('p','wx-status');status.setAttribute('role','status');
  const content=node('div','wx-content');
  header.append(heading,refresh);root.append(header,status,content);container.replaceChildren(root);
  let visible=false, fetching=false, dead=false, lastSuccess=0, lastAttempt=0, timer, controller;
  const shown=()=>visible&&document.visibilityState!=='hidden'&&!container.closest('details:not([open])');
  function schedule(ms){
    clearTimeout(timer);if(shown()&&!dead)timer=setTimeout(()=>load(),ms);
  }
  function expiry(){
    const nextHour=(Math.floor(lastSuccess/hourMs)+1)*hourMs;
    return Math.min(lastSuccess+cacheMs,nextHour);
  }
  async function load(force=false){
    if(!shown()||fetching||dead)return;
    const now=Date.now(),remaining=Math.max(expiry(),lastAttempt>lastSuccess?lastAttempt+30000:0)-now;
    if(!force&&remaining>0){schedule(remaining);return;}
    fetching=true;lastAttempt=now;refresh.disabled=true;
    if(!lastSuccess)status.textContent='予報を読み込んでいます…';
    controller=new AbortController();const timeout=setTimeout(()=>controller.abort(),15000);
    try{
      const url=new URL(endpoint);url.searchParams.set('area',id);
      const res=await fetch(url,{signal:controller.signal,cache:'no-store'});
      if(!res.ok)throw Error('予報を取得できません。');
      const data=await res.json();if(dead)return;
      if(data.area!==id||!Array.isArray(data.hours))throw Error('予報を読み取れません。');
      paint(content,data,area);lastSuccess=Date.now();status.textContent='';schedule(expiry()-lastSuccess);
    }catch{
      if(dead)return;
      status.textContent=lastSuccess?'更新できませんでした。前回取得した予報を表示しています。':'予報を取得できませんでした。「更新」で再試行できます。';
      schedule(60000);
    }finally{clearTimeout(timeout);fetching=false;if(!dead)refresh.disabled=false;}
  }
  function activated(){if(shown())load();else clearTimeout(timer);}
  const ancestor=container.closest('details');
  const observer=new IntersectionObserver(records=>{visible=records.some(r=>r.isIntersecting);activated();});
  observer.observe(root);
  ancestor?.addEventListener('toggle',activated);document.addEventListener('visibilitychange',activated);
  window.addEventListener('online',activated);
  refresh.onclick=()=>load(true);
  function destroy(){
    dead=true;clearTimeout(timer);controller?.abort();observer.disconnect();
    ancestor?.removeEventListener('toggle',activated);document.removeEventListener('visibilitychange',activated);window.removeEventListener('online',activated);
  }
  mounted.set(container,destroy);return destroy;
}
