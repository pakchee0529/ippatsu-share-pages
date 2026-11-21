import {call,linkFor} from './api.mjs';
const root=document.querySelector('#pages');
try{const {items}=await call('sandboxList');for(const item of items){const a=document.createElement('a');a.className='entry';a.href=linkFor(item.id);a.textContent=item.definition.title;root.append(a);}}catch(e){const a=document.createElement('a');a.href='../assistant/';a.textContent=e.message;root.append(a);}
