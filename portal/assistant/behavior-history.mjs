import {editingContext} from './short-edits.mjs';
import {checkStartup} from './sandbox-check.mjs?v=art1';

const marker=/<!--ippatsu-checks:([A-Za-z0-9+/=]+)-->/g;
function readCases(html){
  const data=Array.from((html||'').matchAll(marker)).at(-1)?.[1];
  if(!data)return [];
  try{
    const cases=JSON.parse(new TextDecoder().decode(Uint8Array.from(atob(data),c=>c.charCodeAt(0))));
    return cases.filter(c=>Array.isArray(c)&&c.length<=8&&c.every(s=>s&&typeof s.id==='string'&&['fill','click','expectText','expectValue'].includes(s.action)));
  }catch{return [];}
}
function describe(steps){
  return steps.map(s=>s.action==='click'?s.id+' を押す':s.action==='fill'?s.id+' に入力':s.id+' が「'+s.value+'」になる').join(' → ');
}
export function projectHistory(history,html){
  const cases=readCases(html);
  if(!html)return history;
  const context=editingContext(html);
  if(!cases.length)return [{role:'assistant',text:context},...history.slice(-8)];
  const summary='この版で動作確認済みの操作です。明示された仕様変更を優先し、その他の動きと保存欄のIDは保ってください。\n'+cases.map(describe).join('\n').slice(0,2200);
  return [{role:'assistant',text:[context,summary].join('\n').slice(0,1800)},...history.slice(-7)];
}
export async function preserveBehavior(before,after,steps,approve=window.confirm.bind(window),photo=null){
  const retained=[];
  const key=seq=>JSON.stringify(seq.map(s=>[s.action,s.id,s.value||'']));
  for(const old of readCases(before)){
    if(key(old)===key(steps))continue;
    const error=await checkStartup(after,old,false,photo);
    if(!error)retained.push(old);
    else if(!approve('前の版でできた操作が変わりました。\n'+describe(old)+'\n'+error+'\n今回の仕様変更として、この操作の検査を外しますか？'))throw Error('前の操作を保つため、変更を保留しました。元の下書きから修正を続けられます。');
  }
  if(steps.length)retained.push(steps);
  const html=after.replace(marker,'');
  if(!retained.length)return html;
  const bytes=new TextEncoder().encode(JSON.stringify(retained));
  return html+'<!--ippatsu-checks:'+btoa(Array.from(bytes,b=>String.fromCharCode(b)).join(''))+'-->';
}
