import assert from 'node:assert/strict';
globalThis.document={querySelector:()=>({textContent:'{"date":"261104","cases":[]}'})};
const {applyCard,CODES,FIELDS}=await import('../portal/shared-ledger/read-model.mjs');
class Cell {
 constructor(){this.dataset={quantityState:'confirmed'};this.attrs={};this.textContent='';}
 setAttribute(k,v){this.attrs[k]=v;}
}
export function card(){
 const cells=Object.fromEntries(FIELDS.map(f=>[f,new Cell()])),totals=[new Cell(),new Cell()];let note;
 return {cells,totals,ownerDocument:{createElement:()=>new Cell()},
  querySelector(s){if(s==='.saved-ledger-status')return note;if(s==='.note-panel')return {append:n=>note=n};return cells[s.match(/data-quantity-field="([^"]+)"/)?.[1]];},
  querySelectorAll:s=>s==='.instr-cut-total td'?totals:[],
  snapshot(){return JSON.parse(JSON.stringify({cells,totals,note}));}};
}
const pairs=ds=>ds.map(([width,height],i)=>({id:'SB-'+i,width,height,before:{date:'261104',no:String(i*2+1)},after:{date:'261104',no:String(i*2+2)}}));
function make(base,ds,added){
 const values=Object.fromEntries(CODES.map(c=>[c,c==='SB'?base:0]));
 const records=CODES.map(code=>({code,initial:values[code],mode:'unchanged',revised:null,additional:code==='SB'?added:0}));
 const ui={schema:'ippatsu-photo-ledger-ui/3',trialId:'synthetic-card',revision:1,records:structuredClone(records),pairs:{SB:pairs(ds)},selected:['SB'],clearanceM:null};
 return {entry:{cs:'90000001',base:values},records,document:{case:{case_id:'synthetic-card'},ledger_ui_v3:ui},revision:1,message:'保存済み台帳 版1'};
}
let cases=0;
for(const [base,ds,added,suffix] of [
 [60,[[30,4]],60,'（追加分：30×2／面積割当）'],
 [60,[[40,4]],100,'（追加分：20×1、40×2／面積割当）'],
 [60,[[40,4],[10,2],[5,4]],140,'（追加分：20×1、40×2、10×2、5×4／面積割当）'],
 [65,[[20,4]],15,'（追加分：15×1／面積割当）'],
 [80,[[6,15]],10,'（追加分：4×1、6×1／面積割当）'],
 [0,[[6,4]],24,'（追加分：6×4）'],
 [60,[[30,2]],0,'（30×2）'],
]){
 const p=make(base,ds,added),before=JSON.stringify(p),c=card();applyCard(c,p);
 assert.ok(c.cells.brush_area_m2.textContent.endsWith(suffix));assert.equal(JSON.stringify(p),before);
 const first=c.snapshot();applyCard(c,p);assert.deepEqual(c.snapshot(),first);cases++;
}
const revised=make(80,[[6,15]],30);for(const rs of [revised.records,revised.document.ledger_ui_v3.records])Object.assign(rs.find(r=>r.code==='SB'),{mode:'replace',revised:60});let c=card();applyCard(c,revised);assert.equal(c.cells.brush_area_m2.textContent,'80→60＋30㎡（追加分：6×5／面積割当）');cases++;
const decrease=make(60,[[20,2]],0);for(const rs of [decrease.records,decrease.document.ledger_ui_v3.records])Object.assign(rs.find(r=>r.code==='SB'),{mode:'replace',revised:40});c=card();applyCard(c,decrease);assert.equal(c.cells.brush_area_m2.textContent,'60→40㎡（20×2）');cases++;
for(const mutate of [p=>p.document=null,p=>p.document.ledger_ui_v3.selected=[]]){const p=make(60,[[30,4]],60);mutate(p);c=card();applyCard(c,p);assert.equal(c.cells.brush_area_m2.textContent,'60＋60㎡');cases++;}
const unknown=make(60,[[30,4]],60);c=card();c.cells.brush_area_m2.dataset.quantityState='unknown';c.cells.brush_area_m2.textContent='未確認';applyCard(c,unknown);assert.equal(c.cells.brush_area_m2.textContent,'未確認');cases++;
for(const mutate of [p=>p.records.find(r=>r.code==='SB').additional=59,p=>p.document.ledger_ui_v3.pairs.SB[0].width=null]){
 const p=make(60,[[30,4]],60);mutate(p);c=card();applyCard(c,p);assert.match(c.cells.brush_area_m2.textContent,/追加寸法を確認/);assert.doesNotMatch(c.cells.brush_area_m2.textContent,/30×4/);const before=c.cells.brush_area_m2.textContent;applyCard(c,p);assert.equal(c.cells.brush_area_m2.textContent,before);cases++;
}
console.log(JSON.stringify({cardCases:cases,productionWrites:0}));
