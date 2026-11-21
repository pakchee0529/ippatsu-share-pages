import {surveyNavigation} from './survey-navigation.mjs?v=map3';
import {call} from './api.mjs';
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
 surveyNavigation(item,document.querySelector('#surface'));
 const form=document.querySelector('#page-edit'), adopt=document.querySelector('#adopt'), note=document.querySelector('#edit-status');
 document.querySelector('#edit-panel').hidden=!item.mine;
 let draft;
 form.onsubmit=async e=>{
   e.preventDefault();const button=form.querySelector('button');button.disabled=true;adopt.hidden=true;note.textContent='修正版を作成中…';
   try{const image=await imageInput(form.elements.sketch.files[0]);
     ({draft}=await call('sandboxDraft',{id,revision:item.revision,prompt:form.elements.prompt.value,image}));
     document.querySelector('#candidate').replaceChildren(previewPage(draft.html));adopt.hidden=false;note.textContent='下書きの動きを確認してください。';
   }catch(err){note.textContent=err.message;}finally{button.disabled=false;}
 };
 adopt.onclick=async()=>{adopt.disabled=true;try{await call('sandboxPublish',{id,revision:item.revision,draft});location.reload();}catch(err){note.textContent=err.message;adopt.disabled=false;}};
 remove.hidden=false;
 remove.onclick=async()=>{
   if(!confirm('「'+item.definition.title+'」を全員の砂場から撤去しますか？'))return;
   remove.disabled=true;
   try{await call('sandboxRemove',{id,revision:item.revision});location.replace('./');}
   catch(e){status.textContent=e.message;remove.disabled=false;}
 };
}catch(e){status.textContent=e.message;}


