// Explicit source-only rendering: no imports, fetch, Auth, storage or business events.
const node=document.querySelector('#provisional-readonly-config');
if(!node)throw Error('Readonly source contract missing');
const c=JSON.parse(node.textContent),mode=document.body.dataset.provisionalMode;
if(c.schema!=='ippatsu-provisional-readonly/v1'||c.mode!=='provisional_futaku_readonly'||c.date!=='261118')throw Error('Readonly source scope invalid');
if(mode==='instructions'){
 const cs=new URLSearchParams(location.search).get('management_no');
 if(!c.cases.some(x=>x.management_no===cs)){
  document.querySelector('main').replaceChildren(Object.assign(document.createElement('p'),{textContent:'対象径間がありません。共有入口から選択してください。'}));
  document.documentElement.dataset.provisionalReady='invalid-target';
 }else{
  for(const card of document.querySelectorAll('article[data-management-no-key]'))if(card.dataset.managementNoKey!==cs)card.remove();
  document.documentElement.dataset.provisionalReady='true';
 }
}else document.documentElement.dataset.provisionalReady='true';
