export function surveyTemplate(draft,withNumbers=false){
  const names=draft.names;
  if(!Array.isArray(names)||!names.length||names.some(n=>!/[〜～~]/.test(n)||n.length>100)||new Set(names).size!==names.length)throw Error('径間を確認できませんでした。径間名か、読み取りやすい写真を送ってください。');
  const list=document.createElement('section');list.dataset.surveyRows='';
  for(const name of names){
    const label=document.createElement('label'),input=document.createElement('input');input.type='checkbox';
    input.id='span-'+Array.from(name,c=>c.codePointAt(0).toString(36)).join('-');label.append(input,name);list.append(label);
    const number=withNumbers&&draft.numbers?.find(n=>n.name===name)?.text;
    const review=draft.reviews?.find(r=>r.name===name)?.message;
    if(number||review){
      const group=document.createElement('div');label.replaceWith(group);group.append(label);
      for(const [key,value] of [['referenceNumber',number],['review',review]]){
        if(!value)continue;
        label.dataset[key]=value;const caption=document.createElement('p');caption.textContent=value;group.append(caption);
      }
    }
  }
  const title=draft.title.includes('現調')?draft.title:draft.title+'の現調リスト';
  const h=document.createElement('h1');h.textContent=title;
  return {title,html:'<!doctype html><html lang="ja"><meta charset="utf-8"><style>:root{--ink:#214537;--rule:#d7ded7;font:16px system-ui}body{color:var(--ink);margin:1rem}h1{font-size:1.3rem}label{display:flex;align-items:center;gap:.6rem;min-height:46px;border-bottom:1px solid var(--rule)}</style>'+h.outerHTML+list.outerHTML+'</html>'};
}
