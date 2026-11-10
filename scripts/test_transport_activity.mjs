import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {groups} from '../portal/shared-ledger/ledger-view-model.mjs';
const refs=[{date:'261110',no:'016'},{date:'261110',no:'017'},{date:'261110',no:'018'}];
const CODES=['E10','E20','E30','E40','E50','E60','N10','N20','N30','N40','N50','N60','SB','TK','TR'];
const make=(operations=true)=>({entry:{cs:'90000001',label:'合成試験1～2'},records:CODES.map(code=>({code,initial:0,mode:'unchanged',revised:null,additional:0})),photos:{branchCount:0},document:{case:{work_date:'261110',design_no:'0001'},ledger_ui_v3:{selected:['US'],pairs:{},cuts:{},details:{},special:{US:refs.map(r=>({label:'運搬 2tダンプ',photos:[{...r}]}))},...(operations?{quantityOperations:{version:1,corrections:{}}}:{})}}});
const expected=n=>({type:'運搬',category:'運搬',text:'US×'+n});
const freeze=o=>{if(o&&typeof o==='object'){Object.freeze(o);for(const v of Object.values(o))freeze(v);}return o;};
let cases=0;
for(const operations of [false,true]){
 for(const [mutate,n] of [
  [()=>{},3],
  [p=>p.document.ledger_ui_v3.special.US.push({photos:[{date:'261110',no:'16'},{date:'261110',no:'016'}]}),3],
  [p=>p.document.ledger_ui_v3.special.US.push({photos:[{date:'261109',no:'016'}]}),4],
  [p=>p.document.ledger_ui_v3.special.US=[],0],
  [p=>p.document.ledger_ui_v3.selected=[],null],
  [p=>p.document.ledger_ui_v3.selected=false,null],
  [p=>p.document.ledger_ui_v3.selected={US:false},null],
  [p=>delete p.document.ledger_ui_v3.selected,3],
  [p=>p.document=null,null]
 ]){const p=make(operations);mutate(p);const before=JSON.stringify(p);freeze(p);assert.deepEqual(groups(p),n===null?[]:[expected(n)]);assert.equal(JSON.stringify(p),before);cases++;}
 const p=make(operations);p.document.ledger_ui_v3.selected.push('SB');p.document.ledger_ui_v3.pairs.SB=[{width:3,height:2}];assert.deepEqual(groups(p),[expected(3),{type:'寸法',category:'柴',text:'',dimensions:'3×2'}]);cases++;
}
const native=make(false);native.document={case:{work_date:'261110'},selected:['US'],transport:[{photos:structuredClone(refs)}]};assert.deepEqual(groups(native),[expected(3)]);cases++;
// Requested Nov5 archive presentation. Live count still uses saved photo references;
// the archive completion-note source is not inferred or copied into live data.
const pair='portal/archive/261105/saved-forms/final-ledger-8ad48334ad255b519fa7/';
for(const name of ['daily.html','instructions.html'])assert.match(readFileSync(new URL('../'+pair+name,import.meta.url),'utf8'),/<span class="kind">運搬<\/span><span>運搬<\/span>.*?<span>US×1<\/span>/);
// The same renderer is used for both modes. A small DOM double avoids network/storage.
class Element{
 constructor(tag){this.tag=tag;this.children=[];this.dataset={};this.className='';this.attrs={};this.ownerDocument=globalThis.document;this.classList={add:(x)=>this.className+=' '+x};}
 append(...nodes){this.children.push(...nodes);}
 setAttribute(k,v){this.attrs[k]=v;}
 set textContent(v){this.children=[String(v)];}
 get textContent(){return this.children.map(x=>typeof x==='string'?x:x.textContent).join('');}
 set innerHTML(v){this.children=[String(v)];}
}
globalThis.document={querySelector:s=>s==='#shared-ledger-config'?{textContent:'{"date":"261110","cases":[]}'}:null,createElement:tag=>new Element(tag)};
document.head=new Element('head');
const {renderProjection,instructionPhotoPlan}=await import('../portal/shared-ledger/ledger-view-render.mjs');
for(const operations of [false,true])for(const mode of ['daily','instructions']){
 const p=make(operations),before=JSON.stringify(p),root=new Element('main');renderProjection(root,p,{mode,date:'261110'});
 assert.equal(root.textContent.split('US×3').length-1,1);assert.ok(root.textContent.includes('追加・変更・運搬運搬運搬US×3'));
 assert.equal(JSON.stringify(p),before);assert.deepEqual(instructionPhotoPlan(p.document,p.records).find(x=>x.code==='US').rows,refs);cases++;
}
console.log(JSON.stringify({transportCases:cases,archivePairFormat:true,dailyInstructionsParity:true,productionWrites:0}));
