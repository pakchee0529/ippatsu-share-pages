const icons = [
  ['pin', '地図ピン', /地図|マップ|現調|巡回|ピン/, 'mint', 'M12 21s7-6 7-12a7 7 0 1 0-14 0c0 6 7 12 7 12z M15 9a3 3 0 1 1-6 0 3 3 0 0 1 6 0z'],
  ['check', 'チェック', /チェック|持ちもの|持ち物|タスク/, 'yellow', 'M4 4h16v16H4z M7 12l3 3 7-8'],
  ['camera', 'カメラ', /写真|カメラ|撮影/, 'sky', 'M3 7h4l2-3h6l2 3h4v13H3z M16 13a4 4 0 1 1-8 0 4 4 0 0 1 8 0z'],
  ['calendar', 'カレンダー', /カレンダー|予定表|当番表|日程/, 'sky', 'M3 5h18v16H3z M3 10h18 M7 2v6 M17 2v6 M7 14h3 M13 14h3'],
  ['tool', '工具', /工具|整備|修理/, 'orange', 'M14 4a6 6 0 0 0-6 8l-5 5a2.8 2.8 0 0 0 4 4l5-6a6 6 0 0 0 8-7l-4 3-3-3 3-4z'],
  ['calculator', '電卓', /電卓|計算|見積/, 'mint', 'M5 2h14v20H5z M8 6h8 M8 11h2 M13 11h2 M8 15h2 M13 15h2 M8 18h2 M13 18h2'],
  ['clock', '時計', /時計|時間計測|タイマー|ストップウォッチ/, 'yellow', 'M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0z M12 6v6l4 2'],
  ['note', 'ノート', /ノート|自由帳|メモ/, 'pink', 'M5 3h14v18H5z M8 8h8 M8 12h8 M8 16h5']
];
const colors = {mint:['ミント',/ミント|緑|グリーン/], yellow:['山吹',/山吹|黄|イエロー/], sky:['空色',/空色|水色|青|ブルー/], pink:['桜色',/桜色|桃色|ピンク/],orange:['オレンジ',/オレンジ|橙/]};
const marker=/<!--ippatsu-style:(pin|check|camera|calendar|tool|calculator|clock|note):(mint|yellow|sky|pink|orange)-->/;
export function appearance(d){
  const stored=d.html.match(marker);
  if(stored)return {icon:stored[1],color:stored[2]};
  const doc=new DOMParser().parseFromString(d.html,'text/html');
  const heading=doc.querySelector('h1')?.textContent||'';
  const entry=doc.querySelector('[data-survey-rows]')?icons[0]:icons.find(i=>i[2].test(d.title+' '+heading)) || (doc.querySelector('input[type=checkbox]')?icons[1]:doc.querySelector('input[accept*=image]')?icons[2]:icons.at(-1));
  return {icon:entry[0],color:entry[3]};
}
export function stamp(d,style){
  return {...d,html:d.html.replace(new RegExp(marker.source,'g'),'')+'<!--ippatsu-style:'+style.icon+':'+style.color+'-->'};
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


export const designBrief = 'ページを生成する場合、一覧で使う目印も選ぶ。添付方法や題名の単語より、使う人が主に何をするかを優先。現場を回る=pin、確認を消し込む=check、写真を集める=camera、予定を組む=calendar、修理や整備の履歴=tool、金額や数量の計算=calculator、時間を測る=clock、文章を書く=note。「写真係」の担当日を決めるならcalendar、写真を撮って並べるならcamera。色はページのアクセントに近い mint/yellow/sky/pink/orange。HTMLの末尾に <!--ippatsu-style:種類:色--> を実際の英字に置き換えて一つ入れる。確認質問が必要なときは通常どおり質問する。';
export function reconcilePurpose(draft,request){
  // A subject such as 写真係 names the people or equipment, not the operation.
  const allocation=/(担当者?|係|当番).{0,24}(割り当て|割当|振り分け)|当番表.{0,12}(作|組|管理)|日付ごとに.{0,12}(割り当て|割当)/u;
  if(!allocation.test(request))return draft;
  return stamp(draft,{...appearance(draft),icon:'calendar'});
}
