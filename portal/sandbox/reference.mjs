export function displayReference(text){
  return text.replace(/(^|[／/]\s*)管理番号\s*([0-9０-９]{8})(?=\s*(?:[／/]|$))/gu,'$1$2');
}

export function referenceContent(text,size){
  const fragment=document.createDocumentFragment();
  const value=displayReference(text);
  const match=value.match(/^([0-9０-９]{8})(?=\s*(?:[／/]|$))/u);
  if(!match||!size){fragment.append(value);return fragment;}
  const number=document.createElement('span');
  number.textContent=match[1];number.style.fontSize=size+'px';
  fragment.append(number,value.slice(match[1].length));return fragment;
}

export function resizeReference(request,page){
  if(!page?.html)return;
  const match=request.trim().match(/^管理番号(?:だけ|の文字|の数字|の表示)?(?:を|は)?\s*(?:もっと|もう少し)?(大き|小さ)(?:く|めに|め)?(?:表示)?(?:に)?(?:して|する|お願い)?[。！!]?$/u);
  if(!match)return;
  const doc=new DOMParser().parseFromString(page.html,'text/html');
  const list=doc.querySelector('[data-survey-rows]');if(!list)return;
  const labels=[...list.querySelectorAll('label[data-reference-number]')].filter(el=>/^[0-9０-９]{8}(?=\s*(?:[／/]|$))/.test(displayReference(el.dataset.referenceNumber)));
  if(!labels.length)return {kind:'clarify',message:'このリストに表示できる管理番号がありません。番号付きの下書きなら「管理番号・設計番号をリストに表示」をオンにしてください。'};
  const prior=Number(list.dataset.referenceSize)||16;
  const size=match[1]==='大き'?Math.min(48,prior+6):Math.max(12,prior-4);
  list.dataset.referenceSize=String(size);
  if(list.hasAttribute('data-waiting-list'))list.style.setProperty('--reference-size',size+'px');
  for(const el of labels){
    const caption=el.nextElementSibling;
    if(caption?.tagName==='P')caption.replaceChildren(referenceContent(el.dataset.referenceNumber,size));
  }
  const html='<!doctype html>'+[...doc.childNodes].filter(n=>n.nodeType!==10).map(n=>n.nodeType===8?'<!--'+n.data+'-->':n.outerHTML||'').join('');
  return {kind:'draft',draft:{...page,html},message:'管理番号の数字を'+size+'pxにしました。',steps:[]};
}

const commonWarning='管理番号を送った資料と見比べてください。';
export function surveyWarnings(rows){
  const affected=rows.filter(row=>row.review?.includes(commonWarning));
  if(affected.length<2)return '';
  for(const row of affected)row.review=row.review.replace(commonWarning,'').trim();
  return affected.length===rows.length?'全'+rows.length+'件の管理番号は再確認が必要です。':'管理番号の再確認が必要な径間：'+affected.map(row=>row.name).join('、');
}
