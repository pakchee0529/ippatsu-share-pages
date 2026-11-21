import {imageInput} from "../sandbox/image-input.mjs";
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
const history=[], log=root.querySelector('[role=log]');
let photo;
function message(role,text){
 history.push({role,text});
 const row=document.createElement('div');row.className=role==='user'?'row mine':'row';
 const bubble=document.createElement('p');bubble.className='bubble';bubble.textContent=text;row.append(bubble);log.append(row);
}
function resetThread(){history.length=0;photo=null;draft=null;log.replaceChildren();preview.replaceChildren();publish.hidden=true;form.elements.sketch.value='';result.textContent='';}
select.onchange=resetThread;
form.onsubmit=async e=>{
 e.preventDefault();const btn=form.querySelector('button'),field=form.elements.prompt;
 const prompt=field.value.trim();if(!prompt)return;
 btn.disabled=true;select.disabled=true;publish.disabled=true;
 try{
   const file=form.elements.sketch.files[0];if(file)photo=await imageInput(file);
   target=items.find(i=>i.id===select.value);
   const previousMessages=history.slice(-10);message('user',prompt+(file?'（写真付き）':''));
   result.textContent='いっぱつちゃんが確認中…';
   const reply=await call('sandboxDraft',{interactive:true,prompt,history:previousMessages,previous:draft,image:photo,id:target?.id,revision:target?.revision});
   if(reply.question){message('assistant',reply.question);}
   else{draft=reply.draft;preview.replaceChildren(previewPage(draft.html));message('assistant',draft.title+'の下書きです。触ってみて、直したいところを教えてください。');publish.hidden=false;}
   result.textContent='';field.value='';form.elements.sketch.value='';
 }catch(err){result.textContent=err.message;}finally{btn.disabled=false;select.disabled=false;publish.disabled=false;}
};
publish.onclick=async()=>{publish.disabled=true;try{const item=await call('sandboxPublish',{draft,id:target?.id,revision:target?.revision});publish.hidden=true;result.textContent='掲載しました。';await refresh();select.value=item.id;}catch(e){result.textContent=e.message;}finally{publish.disabled=false;}};
