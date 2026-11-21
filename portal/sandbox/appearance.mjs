const icons = [
  ['pin', '地図ピン', /地図|マップ|現調|巡回|ピン/, 'mint', 'M12 21s7-6 7-12a7 7 0 1 0-14 0c0 6 7 12 7 12z M15 9a3 3 0 1 1-6 0 3 3 0 0 1 6 0z'],
  ['check', 'チェック', /チェック|持ちもの|持ち物|タスク/, 'yellow', 'M4 4h16v16H4z M7 12l3 3 7-8'],
  ['camera', 'カメラ', /写真|カメラ|撮影/, 'sky', 'M3 7h4l2-3h6l2 3h4v13H3z M16 13a4 4 0 1 1-8 0 4 4 0 0 1 8 0z'],
  ['note', 'ノート', /ノート|自由帳|メモ/, 'pink', 'M5 3h14v18H5z M8 8h8 M8 12h8 M8 16h5']
];
const colors = {mint:['ミント',/ミント|緑|グリーン/], yellow:['山吹',/山吹|黄|イエロー/], sky:['空色',/空色|水色|青|ブルー/], pink:['桜色',/桜色|桃色|ピンク/],orange:['オレンジ',/オレンジ|橙/]};
const marker=/<!--ippatsu-style:(pin|check|camera|note):(mint|yellow|sky|pink|orange)-->/;
export function appearance(d){
  const stored=d.html.match(marker);
  if(stored)return {icon:stored[1],color:stored[2]};
  const doc=new DOMParser().parseFromString(d.html,'text/html');
  const heading=doc.querySelector('h1')?.textContent||'';
  const entry=doc.querySelector('[data-survey-rows]')?icons[0]:icons.find(i=>i[2].test(d.title+' '+heading)) || (doc.querySelector('input[type=checkbox]')?icons[1]:doc.querySelector('input[accept*=image]')?icons[2]:icons[3]);
  return {icon:entry[0],color:entry[3]};
}
export function stamp(d,style){
  return {...d,html:d.html.replace(marker,'')+'<!--ippatsu-style:'+style.icon+':'+style.color+'-->'};
}
export function requestedAppearance(text,d){
  if(!/にして|変え|変更|にする|アイコン|色に/.test(text))return;
  const icon=/アイコン|マーク/.test(text)?icons.find(i=>i[2].test(text)):null;
  const color=Object.entries(colors).find(([,v])=>v[1].test(text));
  if(!icon&&!color)return;
  const current=appearance(d);
  const style={icon:icon?.[0]??current.icon,color:color?.[0]??current.color};
  return {style,label:colors[style.color][0]+'の'+icons.find(i=>i[0]===style.icon)[1]};
}
export function decorate(link,d){
  const {icon,color}=appearance(d);
  const svg=document.createElementNS('http://www.w3.org/2000/svg','svg');
  svg.setAttribute('viewBox','0 0 24 24');svg.setAttribute('aria-hidden','true');
  const path=document.createElementNS(svg.namespaceURI,'path');
  path.setAttribute('d',icons.find(i=>i[0]===icon)[4]);svg.append(path);
  link.dataset.color=color;link.prepend(svg);
}

