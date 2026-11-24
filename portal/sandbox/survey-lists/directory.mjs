import {call,linkFor} from '../api.mjs';

const status=document.getElementById('list-status');
const list=document.getElementById('survey-lists');
async function load(){
  status.textContent='リストを読み込んでいます。';
  try{
    const {items}=await call('sandboxList');
    const links=items.filter(item=>item.definition.title.includes('現調')).map(item=>{
      const link=document.createElement('a');
      link.href=linkFor(item.id);
      link.textContent=item.definition.title;
      const row=document.createElement('li');
      row.append(link);
      return row;
    });
    list.replaceChildren(...links);
    status.textContent=links.length?'径間を追加したいリストを開いてください。':'まだ現調リストはありません。';
  }catch{
    status.textContent='リストを読み込めませんでした。 ';
    const retry=document.createElement('button');
    retry.type='button';
    retry.textContent='読み直す';
    retry.onclick=load;
    status.append(retry);
  }
}
await load();
