import {accountButton} from '../account/session.mjs';
accountButton(document.getElementById('account-entry'));
import {decorate} from './appearance.mjs';
import {call,linkFor} from './api.mjs';
const root=document.querySelector('#pages');
decorate(document.getElementById('lunch-map'),{title:'昼休みマップ',html:'<!--ippatsu-style:pin:yellow-->'});
decorate(document.getElementById('daily-photo'),{title:'今日の一枚',html:'<!--ippatsu-style:camera:pink-->'});
try{const {items}=await call('sandboxList');for(const item of items){const a=document.createElement('a');a.className='entry';a.href=linkFor(item.id);a.textContent=item.definition.title;decorate(a,item.definition);root.append(a);}}catch(e){const a=document.createElement('a');a.href='../assistant/';a.textContent=e.message;root.append(a);}

