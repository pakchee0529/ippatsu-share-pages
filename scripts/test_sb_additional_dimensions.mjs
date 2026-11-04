import assert from 'node:assert/strict';
import {additionalBushDimensions,groups} from '../portal/shared-ledger/ledger-view-model.mjs';
const pair=(w,h,i=0)=>({id:'SB-'+i,before:{date:'261104',no:String(i*2+1)},after:{date:'261104',no:String(i*2+2)},width:w,height:h});
const make=(base,pairs,added,operations=false)=>({records:[{code:'SB',initial:base,mode:'unchanged',revised:null,additional:added}],document:{ledger_ui_v3:{selected:['SB'],pairs:{SB:pairs},details:{},special:{},...(operations?{quantityOperations:{version:1,corrections:{}}}:{})}}});
const freeze=o=>{if(o&&typeof o==='object'){Object.freeze(o);for(const v of Object.values(o))freeze(v);}return o;};
const sum=s=>s.split('、').filter(Boolean).reduce((n,t)=>{assert.match(t,/^[1-9]\d*×[1-9]\d*$/);const [w,h]=t.split('×').map(Number);return n+w*h;},0);
let examples=0,exhaustive=0,invalid=0,integration=0;
for(const [b,d,a,expected] of [[60,[[30,4]],60,'30×2'],[60,[[40,4]],100,'20×1、40×2'],[60,[[40,4],[10,2],[5,4]],140,'20×1、40×2、10×2、5×4'],[60,[[20,4]],20,'20×1'],[65,[[20,4]],15,'15×1'],[80,[[6,15]],10,'4×1、6×1'],[78,[[6,15]],12,'6×2'],[89,[[6,15]],1,'1×1'],[0,[[6,15]],90,'6×15'],[8,[[2,3],[4,5]],18,'2×1、4×4'],[6,[[2,3],[4,5]],20,'4×5'],[5,[[2,3],[4,5]],21,'1×1、4×5']]){
 for(const op of [false,true]){const p=freeze(make(b,d.map(([w,h],i)=>pair(w,h,i)),a,op)),before=JSON.stringify(p),result=additionalBushDimensions(p,p.records[0]);assert.equal(result.dimensions,expected);assert.equal(sum(result.dimensions),a);assert.equal(Boolean(result.dimensionAllocation),b>0);const list=groups(p);assert.equal(list.length,1);assert.equal(list[0].dimensions,expected);assert.equal(list[0].count,a);assert.equal(JSON.stringify(p),before);examples++;}
}
for(let w=1;w<=20;w++)for(let h=1;h<=20;h++)for(let b=0;b<w*h;b++){const p=make(b,[pair(w,h)],w*h-b),r=additionalBushDimensions(p,p.records[0]);assert.equal(sum(r.dimensions),w*h-b);assert.ok(!r.dimensionWarning);exhaustive++;}
for(let w=0;w<=7;w++)for(let h=0;h<=7;h++)for(let b=0;b<w*h+6;b++){const p=make(b,[pair(w,h),pair(2,3,1)],w*h+6-b),r=additionalBushDimensions(p,p.records[0]);assert.equal(sum(r.dimensions),w*h+6-b);exhaustive++;}
const mutations=[p=>p.records[0].initial=null,p=>p.records[0].initial=undefined,p=>p.records[0].initial=-1,p=>p.records[0].initial=60.1,p=>p.records[0].initial='60',p=>p.records[0].additional=null,p=>p.records[0].additional=0,p=>p.records[0].additional=59,p=>p.records[0].mode='other',p=>p.document.ledger_ui_v3.pairs.SB=undefined,p=>p.document.ledger_ui_v3.pairs.SB={},p=>p.document.ledger_ui_v3.pairs.SB=[null],p=>p.document.ledger_ui_v3.pairs.SB[0].width=null,p=>p.document.ledger_ui_v3.pairs.SB[0].height=null,p=>p.document.ledger_ui_v3.pairs.SB[0].width='30',p=>p.document.ledger_ui_v3.pairs.SB[0].height=4.5,p=>p.document.ledger_ui_v3.pairs.SB[0].width=-30,p=>p.document.ledger_ui_v3.pairs.SB[0].height=Infinity,p=>p.document.ledger_ui_v3.pairs.SB[0].width=1000001,p=>p.document.ledger_ui_v3.pairs.SB.push(pair(30,4)),p=>{p.document.ledger_ui_v3.pairs.SB.push({...pair(30,4,1),before:{date:'261104',no:'01'},after:{date:'261104',no:'02'}});p.records[0].additional=180;}];
for(const mutate of mutations){const p=make(60,[pair(30,4)],60);mutate(p);const result=additionalBushDimensions(p,p.records[0]);assert.equal(result.dimensions,'');assert.match(result.dimensionWarning,/確認/);invalid++;}
for(const op of [false,true]){
 const p=make(60,[pair(30,4)],60,op);p.document.ledger_ui_v3.pairs.SB[0].width=null;const out=groups(p);assert.equal(out.length,1);assert.equal(out[0].dimensions,'');assert.match(out[0].dimensionWarning,/確認/);integration++;
 const zero=make(60,[pair(30,2)],0,op);assert.deepEqual(groups(zero),[{type:'寸法',category:'柴',text:'',dimensions:'30×2'}]);integration++;
 const decrease=make(60,[pair(20,2)],0,op);decrease.records[0].mode='replace';decrease.records[0].revised=40;assert.ok(!groups(decrease).some(g=>g.type==='追加'));integration++;
 const revised=make(80,[pair(6,15)],30,op);revised.records[0].mode='replace';revised.records[0].revised=60;assert.equal(groups(revised).find(g=>g.type==='追加').dimensions,'6×5');integration++;
 const blank=make(60,[{width:null,height:null,before:{no:''},after:{no:''}},pair(30,4)],60,op);assert.equal(groups(blank).find(g=>g.type==='追加').dimensions,'30×2');integration++;
}
const native=make(60,[pair(30,4)],60);native.document={pairs:native.document.ledger_ui_v3.pairs,selected:['SB'],special:[]};assert.equal(groups(native)[0].dimensions,'30×2');integration++;
console.log(JSON.stringify({examples,exhaustive,invalid,integration,productionWrites:0}));
