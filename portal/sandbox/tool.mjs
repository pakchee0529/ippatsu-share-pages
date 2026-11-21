import {childChat} from './child-chat.mjs?v=fieldcopy1';
import {surveyNavigation} from './survey-navigation.mjs?v=fieldcopy1';
import {call} from './api.mjs?v=child1';
import {previewPage} from './preview.mjs';
import {imageInput} from './image-input.mjs';
const id=new URLSearchParams(location.search).get('id');
const status=document.querySelector('#status');
const remove=document.querySelector('#remove');
try{
 const item=await call('sandboxGet',{id});
 document.querySelector('#title').textContent=item.definition.title;
 const frame=previewPage(item.definition.html,"ippatsu.sandbox.inputs."+id);
 document.querySelector('#surface').append(frame);
 const surface=document.querySelector('#surface'),survey=surveyNavigation(item,surface);
 if(survey){
   const original=new URL(location.href), alternate=document.createElement('a'),panel=document.querySelector('.survey-route');
   const showOriginal=original.searchParams.get('layout')==='original';
   if(showOriginal){surface.hidden=false;panel.hidden=true;original.searchParams.delete('layout');}
   else original.searchParams.set('layout','original');
   alternate.href=original.href;alternate.textContent=showOriginal?'巡回地図に戻る':'作成したページのレイアウトで開く';
   surface.after(alternate);
 }
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
