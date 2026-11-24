/** Apply an unambiguous copy edit without regenerating the rest of the page. */
export function literalEdit(request,previous){
  if(!previous?.html)return;
  const match=request.trim().match(/^(?:文言|表示|ラベル|ボタン名)?[「『]([^「」『』\n]+)[」』](?:の(?:文字|文言|表示))?を[「『]([^「」『』\n]+)[」』](?:に(?:変更|修正|置換|変え|替え|書き換え|し)(?:して|て|る)?|に)[。！!]?$/u);
  if(!match)return;
  const [,from,to]=match;
  const doc=new DOMParser().parseFromString(previous.html,'text/html');
  const walker=doc.createTreeWalker(doc.body,NodeFilter.SHOW_TEXT);
  const hits=[];
  while(walker.nextNode()){
    const node=walker.currentNode;
    if(node.textContent.trim()===from&&!node.parentElement.closest('script,style,textarea,template,noscript'))hits.push(node);
  }
  // Preserve source formatting, stored field IDs, scripts and published page metadata.
  // Ambiguous or encoded markup is handled by the ordinary development turn.
  if(hits.length!==1 || previous.html.split(from).length!==2 || !from.length)return;
  const encoded=to.replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;');
  return {kind:'draft',message:'「'+from+'」を「'+to+'」に変更しました。',draft:{...previous,html:previous.html.replace(from,()=>encoded)},steps:[]};
}

export function editingContext(html){
  if(!html)return '';
  const doc=new DOMParser().parseFromString(html,'text/html');
  const elements=[...doc.body.querySelectorAll('h1,h2,h3,button,label,th,summary,nav a')];
  const labels=elements.map(el=>(el.textContent||'').trim().replace(/\s+/g,' ').slice(0,45)).filter(Boolean);
  return '編集中のページの見出し・操作名：'+[...new Set(labels)].slice(0,24).join('、')+'。短い依頼は直前の会話とこの版を参照し、具体的に特定できる部分を変更する。複数の意味で結果が変わる時だけ対象を一つ質問する。相談・質問には説明を返す。指定していない動作・保存欄・入力値は保つ。';
}
import {localInstruction,matchesTarget} from '../sandbox/local-instruction.mjs';
export function targetedEdit(request,previous){
 if(!previous?.html)return;
 const instruction=localInstruction(request);if(!instruction)return;
 const doc=new DOMParser().parseFromString(previous.html,'text/html');
 const matches=matchesTarget(doc.querySelectorAll('h1,h2,h3,button,label,th,summary'),instruction.target);
 if(matches.length>1)return {kind:'clarify',message:'「'+instruction.target+'」に当てはまる箇所が複数あります。変えたい箇所の表示名を教えてください。'};
 if(matches.length!==1)return;
 const el=matches[0];
 if(doc.querySelector('[data-survey-rows]')&&!el.matches('h1'))return;
 const textNodes=[...el.childNodes].filter(n=>n.nodeType===3&&n.textContent.trim());
 const wrapper=el.querySelector(':scope > [data-edit-caption]');
 if(!wrapper&&(textNodes.length!==1||textNodes[0].textContent.trim()!==el.textContent.trim()))return;
 let title=previous.title;
 if(instruction.property==='text'){
   (wrapper||textNodes[0]).textContent=instruction.value;
   if(el.matches('h1')&&(doc.querySelector('[data-survey-rows]')||previous.title===instruction.target))title=instruction.value;
 }else{
   const span=wrapper||doc.createElement('span');
   if(!wrapper){textNodes[0].replaceWith(span);span.append(textNodes[0]);span.dataset.editCaption='';}
   const scale=Number(span.dataset.scale)||1;
   const next=Math.min(3,Math.max(.65,scale*(instruction.delta>0?1.25:.8)));
   span.dataset.scale=String(next);span.style.fontSize=next+'em';
 }
 const html='<!doctype html>'+[...doc.childNodes].map(n=>n.nodeType===1?n.outerHTML:n.nodeType===8?'<!--'+n.data+'-->':'').join('');
 return {kind:'draft',message:'「'+instruction.target+'」の表示を変更しました。',draft:{...previous,title,html},steps:[]};
}
