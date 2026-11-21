import {call,linkFor} from '../sandbox/api.mjs';
import {previewPage} from '../sandbox/preview.mjs';
const root=document.querySelector('#sandbox-tools'), form=root.querySelector('form'), select=form.elements.target, result=root.querySelector('[role=status]'), preview=root.querySelector('.sandbox-preview'), publish=root.querySelector('.sandbox-publish');
let items=[],draft=null,target=null;
async function refresh(){
 try{({items}=await call('sandboxList'));select.replaceChildren(new Option('新しいページ',''));const links=root.querySelector('.sandbox-pages');links.replaceChildren();
 for(const item of items){const a=document.createElement('a');a.className='result-link';a.href=linkFor(item.id);a.textContent=item.definition.title;links.append(a);if(item.mine)select.add(new Option(item.definition.title,item.id));}}
 catch(e){result.textContent=e.message;}
}
document.querySelector('#sandbox-mode').addEventListener('click',refresh);
if(!root.hidden)refresh();
form.onsubmit=async e=>{e.preventDefault();const btn=form.querySelector('button');btn.disabled=true;publish.hidden=true;preview.replaceChildren();result.textContent='下書きを作成中…';target=items.find(i=>i.id===select.value);try{({draft}=await call('sandboxDraft',{prompt:form.elements.prompt.value,id:target?.id,revision:target?.revision}));preview.append(previewPage(draft.html));result.textContent=draft.title;publish.hidden=false;}catch(e){result.textContent=e.message;}finally{btn.disabled=false;}};
publish.onclick=async()=>{publish.disabled=true;try{const item=await call('sandboxPublish',{draft,id:target?.id,revision:target?.revision});publish.hidden=true;result.textContent='掲載しました。';await refresh();select.value=item.id;}catch(e){result.textContent=e.message;}finally{publish.disabled=false;}};
