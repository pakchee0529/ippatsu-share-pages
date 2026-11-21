import {call} from './api.mjs';
import {previewPage} from './preview.mjs';
const id=new URLSearchParams(location.search).get('id');
const status=document.querySelector('#status');
const remove=document.querySelector('#remove');
try{
 const item=await call('sandboxGet',{id});
 document.querySelector('#title').textContent=item.definition.title;
 const frame=previewPage(item.definition.html,"ippatsu.sandbox.inputs."+id);
 document.querySelector('#surface').append(frame);
 remove.hidden=false;
 remove.onclick=async()=>{
   if(!confirm('「'+item.definition.title+'」を全員の砂場から撤去しますか？'))return;
   remove.disabled=true;
   try{await call('sandboxRemove',{id,revision:item.revision});location.replace('./');}
   catch(e){status.textContent=e.message;remove.disabled=false;}
 };
}catch(e){status.textContent=e.message;}
