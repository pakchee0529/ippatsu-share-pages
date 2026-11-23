const units = '袋|箱|台|人|枚|本|個|件';
const starter = new RegExp('^(?:(資材|荷物|部品|道具|車両|参加者)の)?(?:('+units+')数を数える(?:ページ|道具)|('+units+')を数える(?:ページ|道具)|('+units+')数カウンター)(?:を)?(?:作って|作成して|ください|ほしい)?[。！!]*(.*)$');
export function basicCounter(payload){
  if(payload.previous||payload.id||payload.template||payload.pdf||payload.image||payload.attachmentText||payload.history?.length)return;
  const text=payload.prompt.normalize('NFKC').replace(/[\s「」]/g,'');
  const parts=starter.exec(text);
  if(!parts)return;
  const unit=parts[2]||parts[3]||parts[4];
  const spec=parts[5];
  const format=new RegExp('^(?:最初は(\\d{1,5})'+unit+'(?:で|から)[、,]?)?(?:(\\d{1,4})'+unit+'追加を押すと(\\d{1,4})'+unit+'増えるようにして)?[。！!]*$');
  const settings=format.exec(spec);
  if(!settings||settings[2]!==settings[3]||settings[2]==='0')return;
  const initial=Number(settings[1]||0), increment=Number(settings[2]||1);
  if(increment<1)return;
  const title=(parts[1]||'')+unit+'数カウンター';
  const html=`<!doctype html><html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><style>
  :root{color-scheme:light;font-family:system-ui,sans-serif;color:#183a36;background:#f6f4ed}*{box-sizing:border-box}body{margin:0;padding:clamp(18px,6vw,48px)}main{max-width:30rem;margin:auto}h1{font-size:1.45rem}label{display:block;margin-top:2rem}section{display:flex;align-items:baseline;gap:.5rem;margin:.3rem 0 1.6rem}input{background:none;border:0;color:inherit;font:700 clamp(3rem,13vw,5rem)/1.1 system-ui;width:5ch;max-width:85%}button{width:100%;min-height:56px;border:0;border-radius:12px;background:#17594b;color:white;font:700 1.2rem system-ui}button:active{background:#103f36}</style></head><body><main><h1>${title}</h1><label for="count">現在の数</label><section><input id="count" readonly value="${initial}"><span>${unit}</span></section><button id="add">${increment}${unit}追加</button></main><script>
  const count=document.querySelector('#count');document.querySelector('#add').onclick=()=>{count.value=String(Number(count.value)+${increment});count.dispatchEvent(new Event('input',{bubbles:true}));};</script></body></html><!--ippatsu-style:calculator:mint-->`;
  return {draft:{title,html},steps:[{action:'click',id:'add',value:''},{action:'expectValue',id:'count',value:String(initial+increment)}]};
}
