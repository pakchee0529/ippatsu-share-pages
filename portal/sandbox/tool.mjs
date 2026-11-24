import {childChat} from './child-chat.mjs?v=local2';
import {surveyNavigation} from './survey-navigation.mjs?v=rows1';
import {call} from './api.mjs?v=child1';
import {previewPage} from './preview.mjs?v=shared1';
import {imageInput} from './image-input.mjs';
const id=new URLSearchParams(location.search).get('id');
const status=document.querySelector('#status');
const remove=document.querySelector('#remove');
try{
 const item=await call('sandboxGet',{id});
 document.querySelector('#title').textContent=item.definition.title;
 const notice=document.createElement('p');notice.setAttribute('role','status');status.after(notice);
 let writes=Promise.resolve();
 const queued=new Map();
 function save(field,value){
   if(!sessionStorage.getItem('ippatsu.chat.session')){notice.textContent='保存するにはログインしてください。';return;}
   queued.set(field,value);
   writes=writes.then(async()=>{
     if(!queued.has(field))return;
     const latest=queued.get(field);queued.delete(field);
     notice.textContent='保存中…';
     try{await call('sandboxSetInput',{id,revision:item.revision,field,value:latest});notice.textContent='保存しました。';}
     catch(e){notice.textContent='保存できませんでした。'+e.message;}
   });
 }
 const shared={values:item.shared_inputs||{},save};
 const surface=document.querySelector('#surface'),survey=surveyNavigation(item,surface,shared);
 if(!survey)surface.append(previewPage(item.definition.html,"ippatsu.sandbox.inputs."+id,shared));
 if(!sessionStorage.getItem('ippatsu.chat.session')){
   const link=document.createElement('a');link.href='../assistant/?mode=sandbox';link.textContent='いっぱつちゃんで編集する';status.replaceChildren(link);
 }else{
 childChat(item,survey);
 const form=document.querySelector('#page-edit'), adopt=document.querySelector('#adopt'), note=document.querySelector('#edit-status');
 document.querySelector('#edit-panel').hidden=false;
 let draft;
 form.onsubmit=async e=>{
   e.preventDefault();const button=form.querySelector('button');button.disabled=true;adopt.hidden=true;note.textContent='下書きを作っています…';
   try{const image=await imageInput(form.elements.sketch.files[0]);
     ({draft}=await call('sandboxDraft',{id,revision:item.revision,prompt:form.elements.prompt.value,image}));
     document.querySelector('#candidate').replaceChildren(previewPage(draft.html));adopt.hidden=false;note.textContent='下書きの動きを確認してください。';
   }catch(err){note.textContent=err.message;}finally{button.disabled=false;}
 };
 adopt.onclick=async()=>{adopt.disabled=true;try{await call('sandboxPublish',{id,revision:item.revision,draft});location.reload();}catch(err){note.textContent=err.message;adopt.disabled=false;}};
 remove.hidden=false;
 remove.onclick=async()=>{
   if(!confirm('「'+item.definition.title+'」をみんなの砂場から外しますか？'))return;
   remove.disabled=true;
   try{await call('sandboxRemove',{id,revision:item.revision});location.replace('./');}
   catch(e){status.textContent=e.message;remove.disabled=false;}
 };
 }
 }catch(e){
 status.textContent=e.message;
 if(!sessionStorage.getItem('ippatsu.chat.session')||e.status===401){
   const form=document.querySelector('#child-login');form.hidden=false;
   form.onsubmit=async event=>{event.preventDefault();form.querySelector('button').disabled=true;
     try{const result=await call('login',{pin:form.elements.pin.value});sessionStorage.setItem('ippatsu.chat.session',result.token);location.reload();}
     catch(error){status.textContent=error.message;}finally{form.querySelector('button').disabled=false;}
   };
 }
}

