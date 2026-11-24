import {displayReference,surveyWarnings} from '../sandbox/reference.mjs?v=waiting1';

const norm=name=>name.normalize('NFKC').replace(/\s/g,'').replace(/[〜～]/g,'~');
const validSpan=name=>typeof name==='string' && /[〜～~]/.test(name) && name.length<=100;
const uuid=/^[0-9a-f]{8}-(?:[0-9a-f]{4}-){3}[0-9a-f]{12}$/i;

function legacyRows(draft){
  const names=Array.isArray(draft.names)?draft.names:[];
  return names.map((name,i)=>{
    const references=(draft.numbers||[]).filter(n=>n.name===name).map(n=>n.text);
    const reviews=(draft.reviews||[]).filter(r=>r.name===name).map(r=>r.message);
    const ambiguous=names.filter(n=>n===name).length>1;
    if(ambiguous)reviews.push('同名の行があります。'+(references.length?'番号候補 '+[...new Set(references)].join('、')+'。':'')+'原票と照合してください。');
    return {row:i+1,name,reference:!ambiguous && references.length===1?references[0]:'',review:[...new Set(reviews)].join(' ')};
  });
}
function reviewText(r){
  return [r.row?'原票'+r.row+'行目':'原票行',r.name||'径間名未確認',r.management_no||r.number||'',r.design||'',r.message||r.review||'原票を確認してください。'].filter(Boolean).join('　');
}
export function surveyTemplate(draft,withNumbers=true){
  const compact=draft.source==='db-survey-wait';
  const input=Array.isArray(draft.rows)?draft.rows:legacyRows(draft);
  const held=[...(draft.held||[])],duplicates=[...(draft.duplicates||[])],cases=new Map(),rows=[];
  for(const [i,r] of input.entries()){
    const row={...r,row:r.row??i+1};
    if(!validSpan(row.name)){held.push(row);continue;}
    const id=uuid.test(row.case_id)?row.case_id.toLowerCase():null;
    if(id && cases.has(id)){
      const first=cases.get(id);
      if(norm(first.name)===norm(row.name) && (!first.management_no || !row.management_no || first.management_no===row.management_no)){
        duplicates.push({...row,firstRow:first.row,message:'同じ案件としてまとめました。'});
      }else held.push({...row,message:'同じ案件の照合情報が異なります。原票を確認してください。'});
      continue;
    }
    if(id)cases.set(id,row);
    rows.push(row);
  }
  if(!rows.length&&!held.length)throw Error('径間を確認できませんでした。径間名か、読み取りやすい写真を送ってください。');
  const list=document.createElement('section');list.dataset.surveyRows='';
  if(compact)list.dataset.waitingList='';
  const names=rows.map(row=>norm(row.name));
  for(const [i,row] of rows.entries()){
    if(names.indexOf(names[i])!==names.lastIndexOf(names[i])){
      row.review=[row.review,'同名の径間があります。管理番号と原票を確認してください。'].filter(Boolean).join(' ');
    }
  }
  const summary=surveyWarnings(rows);
  if(summary){const note=document.createElement('p');note.dataset.surveyWarning='';note.textContent=summary;list.append(note);}
  for(const [i,row] of rows.entries()){
    const {name,review}=row;
    const label=document.createElement('label'),input=document.createElement('input');input.type='checkbox';
    const oldKey='span-'+Array.from(name,c=>c.codePointAt(0).toString(36)).join('-');
    input.id=uuid.test(row.case_id)?'span-case-'+row.case_id.toLowerCase():
      names.indexOf(names[i])===names.lastIndexOf(names[i]) && oldKey.length<=120?oldKey:'span-row-'+(i+1);
    if(compact && uuid.test(row.case_id)){
      const bytes=row.case_id.replaceAll('-','').match(/../g).map(x=>parseInt(x,16));
      input.id='c-'+btoa(String.fromCharCode(...bytes)).replaceAll('+','-').replaceAll('/','_').replace(/=+$/,'');
    }
    label.append(input,name);list.append(label);
    const number=withNumbers&&(row.reference||row.management_no);
    if(compact && !review){
      if(number)label.dataset.referenceNumber=displayReference(number);
      continue;
    }
    if(number||review){
      const group=document.createElement('div');label.replaceWith(group);group.append(label);
      for(const [key,value] of [['referenceNumber',number],['review',review]]){
        if(!value)continue;
        label.dataset[key]=value;const caption=document.createElement('p');caption.textContent=key==='referenceNumber'?displayReference(value):value;group.append(caption);
      }
    }
  }
  for(const [heading,records] of [['要確認',held],['同じ案件にまとめた行',duplicates]]){
    if(!records.length)continue;
    const section=document.createElement('section');section.dataset.surveyNotices='';
    const title=document.createElement('h2');title.textContent=heading+'（'+records.length+'件）';section.append(title);
    for(const r of records){const line=document.createElement('p');line.textContent=reviewText(r)+(r.firstRow?'　原票'+r.firstRow+'行目に統合':'');section.append(line);}
    list.append(section);
  }
  const title=draft.title.includes('現調')?draft.title:draft.title+'の現調リスト';
  const h=document.createElement('h1');h.textContent=title;
  return {title,html:'<!doctype html><html lang="ja"><meta charset="utf-8"><style>:root{--ink:#214537;--rule:#d7ded7;font:16px system-ui}body{color:var(--ink);margin:1rem}h1{font-size:1.3rem}label{display:flex;align-items:center;gap:.6rem;min-height:46px;border-bottom:1px solid var(--rule)}[data-waiting-list]>label[data-reference-number]::after{content:attr(data-reference-number);margin-left:auto;font-size:var(--reference-size,.88em)}</style>'+h.outerHTML+list.outerHTML+'</html>'};
}
