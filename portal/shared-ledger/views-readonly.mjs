import {renderProjection} from './ledger-view-render.mjs?v=20261113-weekly-source-r1';
const node=document.querySelector('#weekly-source-config');
if(!node)throw Error('Public source configuration missing');
const config=JSON.parse(node.textContent);
if(config.schema!=='ippatsu-weekly-source-format/v1'||!['261116','261117','261118','261119','261120'].includes(config.date))throw Error('Public source scope mismatch');
const mode=document.body.dataset.shareView;
if(mode){
 document.querySelector('h1').textContent='20'+config.date.slice(0,2)+'/'+config.date.slice(2,4)+'/'+config.date.slice(4)+' '+(mode==='daily'?'日次離隔表':'指示書');
 const wanted=new URLSearchParams(location.search).get('management_no');
 const selected=mode==='instructions'?config.cases.filter(x=>x.cs===wanted):config.cases;
 const content=document.querySelector('#content');
 if(!selected.length)document.querySelector('#error').textContent='対象径間がありません。共有入口から選択してください。';
 for(const entry of selected){
  const holder=document.createElement('div');holder.innerHTML=entry.conditions;
  const notes=document.createElement('div');notes.innerHTML=entry.notes;
  const records=entry.quantities.map(q=>({code:q.code,initial:null,mode:'unchanged',revised:null,additional:0,sourceText:q.text,sourceState:q.state,sourceField:q.field}));
  renderProjection(content,{entry,records,document:null,revision:null,sourceOnly:true,message:'原典参照・閲覧専用。正式保存情報は未確認です。',photos:{states:{},branchCount:0}},{mode,date:config.date,conditions:holder.firstElementChild,notes:[notes],mapLink:entry.mapLink});
 }
}
document.documentElement.dataset.sourceViewReady='true';
