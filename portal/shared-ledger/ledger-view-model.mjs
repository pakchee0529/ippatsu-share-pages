import {documentDesignNumber,normalizeDesignNumber} from './design-number.mjs?v=20261110-transport-r1';
import {sectionActive,normalizedSelection} from './special-summary.mjs?v=20261110-transport-r1';
import {totalText,publicQuantityText} from './quantity-format.mjs?v=20261110-transport-r1';
export {totalText};
const names={広葉樹:'広',広:'広',杉:'杉',桧:'桧',松:'松',槙:'槙',梅:'梅',柿:'柿'},rank={広:0,杉:1,桧:2,松:3,槙:4,梅:5,柿:6},kinds=[['E','枝切り'],['N','根切り'],['TK','竹'],['TR','つる'],['SB','柴']],bands={10:'10cm未満',20:'10～20cm',30:'20～30cm',40:'30～40cm',50:'40～50cm',60:'50cm以上'};
const size=n=>n==='70+'?Infinity:Number(n),unit=c=>c==='SB'?'㎡':c==='TR'?'箇所':'本',show=n=>n===null||n===undefined?'—':String(n);
function order(rs){return [...rs].sort((a,b)=>{const prefix=c=>c[0]==='E'?'E':c[0]==='N'?'N':c;return kinds.findIndex(([c])=>c===prefix(a.code))-kinds.findIndex(([c])=>c===prefix(b.code))||Number(a.code.slice(1))-Number(b.code.slice(1));});}
function additionalDetails(p,r){const group=new Map();for(const x of ledgerUI(p.document)?.details?.[r.code]||[]){const species=names[x.species];if(x.kind!=='added'||x.changeFrom||!species||!(x.diameter==='70+'||Number.isFinite(x.diameter)&&x.diameter>0)||!Number.isSafeInteger(x.count)||x.count<=0)continue;const key=species+'|'+x.diameter,old=group.get(key);group.set(key,{kind:'tree',shape:r.code[0]==='E'?'square':'circle',species,diameter:x.diameter,count:(old?.count||0)+x.count});}return [...group.values()].sort((a,b)=>rank[a.species]-rank[b.species]||size(a.diameter)-size(b.diameter));}
function label(code){return code[0]==='E'?'枝切り '+bands[code.slice(1)]:code[0]==='N'?'根切り '+bands[code.slice(1)]:{TK:'竹',TR:'つる',SB:'柴'}[code];}
// Display only. Allocate the existing base area in saved pair order; never
// infer historical shapes or change a saved/projected quantity.
export function additionalBushDimensions(p,r){
 const invalid=()=>({dimensions:'',dimensionWarning:'追加寸法を確認してください（保存面積と寸法を照合できません）'});
 const integer=n=>Number.isSafeInteger(n)&&n>=0&&n<=1000000;
 if(!r||!['unchanged','replace'].includes(r.mode))return invalid();
 const base=r.mode==='replace'?r.revised:r.initial,added=r.additional;
 if(!integer(base)||!integer(added)||added===0||!integer(base+added))return invalid();
 const pairs=ledgerUI(p.document)?.pairs?.SB;
 if(!Array.isArray(pairs))return invalid();
 const rows=[],ids=new Set(),photos=new Set();let area=0;
 const refKey=ref=>ref&&/^\d{6}$/.test(ref.date||'')&&/^\d{1,3}$/.test(String(ref.no??''))&&Number(ref.no)>0?ref.date+':'+Number(ref.no):null;
 for(const pair of pairs){
  if(!pair||typeof pair!=='object'||Array.isArray(pair))return invalid();
  const active=Boolean(pair.before?.no||pair.after?.no||pair.width!==null&&pair.width!==undefined||pair.height!==null&&pair.height!==undefined);
  if(!active)continue;
  if(!integer(pair.width)||!integer(pair.height))return invalid();
  if(pair.id!==undefined&&pair.id!==null&&pair.id!==''){
   if(typeof pair.id!=='string'||ids.has(pair.id))return invalid();
   ids.add(pair.id);
  }
  const before=refKey(pair.before),after=refKey(pair.after),key=before&&after?before+'|'+after:null;
  if(key&&photos.has(key))return invalid();
  if(key)photos.add(key);
  const size=pair.width*pair.height;
  if(!integer(size)||!integer(area+size))return invalid();
  area+=size;rows.push({width:pair.width,height:pair.height,area:size});
 }
 if(area!==base+added)return invalid();
 let remaining=base;const parts=[];
 const append=(width,height)=>{if(width>0&&height>0)parts.push({width,height});};
 for(const row of rows){
  const used=Math.min(remaining,row.area);remaining-=used;
  if(used===row.area)continue;
  if(used===0){append(row.width,row.height);continue;}
  const full=Math.floor(used/row.width),tail=used%row.width;
  if(tail===0)append(row.width,row.height-full);
  else{append(row.width-tail,1);append(row.width,row.height-full-1);}
 }
 if(remaining!==0||parts.reduce((sum,x)=>sum+x.width*x.height,0)!==added)return invalid();
 return {dimensions:parts.map(x=>x.width+'×'+x.height).join('、'),dimensionAllocation:base>0};
}
function dimensions(p){return (ledgerUI(p.document)?.pairs?.SB||[]).filter(x=>Number.isInteger(x.width)&&Number.isInteger(x.height)).map(x=>x.width+'×'+x.height).join('、');}
// r10: merge only SB same-area actual-dimensions display onto current r7d groups (keep auto + import versions).
// Transport is independent of the quantity-editing format. Keep the adopted
// unique photo-date/number count and explicit section selection in both paths.
function transportGroups(p){
 const ui=ledgerUI(p.document);
 if(!p.document||!ui?.selected?.includes('US'))return [];
 const refs=new Set();
 for(const row of ui.special?.US||[])for(const x of row.photos||[])if(x.date&&x.no)refs.add(x.date+':'+Number(x.no));
 return [{type:'運搬',category:'運搬',text:'US×'+refs.size}];
}
function groups(p){const out=[...baseGroups(p),...transportGroups(p)],hasBushAddition=out.some(g=>g.type==='追加'&&g.category===label('SB')),dims=!hasBushAddition&&p.document&&sectionActive(p.document,'SB')?dimensions(p):'';if(dims&&!out.some(g=>g.category===label('SB')&&(g.dimensions||/×/.test(g.text||''))))out.push({type:'寸法',category:label('SB'),text:'',dimensions:dims});return out;}
function baseGroups(p){if(!p.document)return [];if(ledgerUI(p.document)?.quantityOperations)return operationGroups(p);const out=[],ui=ledgerUI(p.document),changes=[];for(const [code,rows] of Object.entries(ui?.details||{}))for(const row of rows)if(row.kind==='changed')changes.push({code,row,source:row.oldCode||code});changes.sort((a,b)=>{const keys=order([...new Set(changes.map(x=>x.source))].map(code=>({code}))).map(x=>x.code);return keys.indexOf(a.source)-keys.indexOf(b.source)||(rank[names[a.row.oldSpecies]]??99)-(rank[names[b.row.oldSpecies]]??99)||size(a.row.oldDiameter)-size(b.row.oldDiameter);});for(const r of order(p.records)){if(!(r.additional>0))continue;const tree=/^[EN]/.test(r.code),items=tree?additionalDetails(p,r):[],known=items.reduce((n,x)=>n+x.count,0);out.push({type:'追加',category:label(r.code),count:r.additional,unit:unit(r.code),items,missing:tree?Math.max(0,r.additional-known):0,auto:tree&&(ui?.details?.[r.code]||[]).some(x=>x.kind==='added'&&x.allocationGenerated),...(r.code==='SB'?additionalBushDimensions(p,r):{dimensions:''})});}for(const {code,row,source} of changes)out.push({type:'変更',category:label(source),sortCode:source,treeChange:{shape:code[0]==='E'?'square':'circle',before:{shape:source[0]==='E'?'square':'circle',species:names[row.oldSpecies],diameter:row.oldDiameter,count:row.oldCount},after:{shape:code[0]==='E'?'square':'circle',species:names[row.species],diameter:row.diameter,count:row.count}}});for(const r of order(p.records)){if(r.mode!=='replace'||r.revised===r.initial)continue;let prior=r.initial;if(/^[EN]/.test(r.code)){let detailDelta=0;for(const x of changes){if(!x.row.oldCode||!Number.isSafeInteger(x.row.oldCount)||!Number.isSafeInteger(x.row.count))continue;if(x.source===r.code)detailDelta-=x.row.oldCount;if(x.code===r.code)detailDelta+=x.row.count;}prior=r.initial===null?null:r.initial+detailDelta;if(prior===r.revised)continue;}const before=r.code==='SB'?(ui?.dimensionHistory?.SB?.before||[]).map(x=>x.width+'×'+x.height).join('、'):'',after=r.code==='SB'?dimensions(p):'';out.push({type:'変更',category:label(r.code),sortCode:r.code,text:'☆'+publicQuantityText(prior)+unit(r.code)+(before?'('+before+')':'')+'→'+publicQuantityText(r.revised)+unit(r.code)+(after?'('+after+')':'')});}const orderedChanges=order(out.filter(x=>x.type==='変更').map((x,i)=>({code:x.sortCode,i}))).map(x=>out.filter(g=>g.type==='変更')[x.i]);const additions=out.filter(x=>x.type==='追加');out.splice(0,out.length,...additions,...orderedChanges);return out;}


export function ledgerUI(d){if(d?.ledger_ui_v3){const ui=d.ledger_ui_v3;return Array.isArray(ui.selected)?ui:{...ui,selected:normalizedSelection(d,['BA',...['E','N'].flatMap(p=>[10,20,30,40,50,60].map(n=>p+n)),'TK','TR','SB','US','DF','SL','HL','BV','RT','FR'])};}const special={US:d?.transport||[]};for(const r of d?.special||[])(special[r.code]??=[]).push(r);return {selected:['BA',...['E','N'].flatMap(p=>[10,20,30,40,50,60].map(n=>p+n)),'TK','TR','SB','US','DF','SL','HL','BV','RT','FR'].filter(c=>sectionActive(d,c)),details:{},cuts:d?.cuts||{},pairs:d?.pairs||{},special};}
export function normalizeProjection(p){if(!p.document)return p;if(ledgerUI(p.document)?.quantityOperations)return p;const rs=p.records.map(r=>({...r}));for(const [code,rows] of Object.entries(ledgerUI(p.document).details||{}))for(const row of rows)if(row.kind==='changed'&&(row.oldCount===null||row.count===null)){for(const key of [code,row.oldCode]){const r=rs.find(x=>x.code===key);if(r){r.mode='replace';r.revised=null;}}}return {...p,records:rs};}
export function workItems(p){if(!p.document)return '';const ui=ledgerUI(p.document),out=[];for(const [c,name,field,unit] of [['DF','倒木実費'],['SL','傾斜木実費'],['HL','吊り切り実費'],['BV','高所作業車','heightM','m'],['RT','ラフター','capacityT','t']])if(ui.selected.includes(c)){const rows=ui.special[c]||[];if(rows.length)out.push(name+(field?' '+rows.map(r=>show(r[field])+unit).join('、'):''));}return out.join(' ／ ');}
export {order,label,groups,show,unit};

// A saved per-span measurement in metres, independent of photo-section visibility.
export function clearanceText(document){
 const ui=document?.ledger_ui_v3;
 const n=ui&&Object.hasOwn(ui,'clearanceM')?ui.clearanceM:document?.clearanceM;
 if(n===undefined||n===null)return '未入力';
 if(typeof n!=='number'||!Number.isFinite(n)||n<0||n>1000||Math.abs(n*10-Math.round(n*10))>1e-8)return '要確認';
 return String(n)+' m';
}

export function designText(document,sourceDesign=null){return (document?documentDesignNumber(document):normalizeDesignNumber(sourceDesign))??'未入力';}

// Display boundary only: sourceCode's 1..999cm contract, no saved-data conversion.
function sourceDiameter(value){if(typeof value==='number')return Number.isInteger(value)&&value>0&&value<=999?value:null;if(typeof value==='string'&&/^\d{1,3}$/.test(value)){const n=Number(value);return n>0&&n<=999?n:null;}return null;}
const cutShape=cut=>cut==='根'?'circle':['枝','芯'].includes(cut)?'square':undefined;
function operationGroups(p){const ui=ledgerUI(p.document),op=ui.quantityOperations,out=[];
for(const r of order(p.records)){const c=r.code;if(Object.hasOwn(op.baseCorrections||{},c))out.push({type:'修正',category:label(c),text:show(r.initial)+unit(c)+' を '+show(op.baseCorrections[c])+unit(c)+' に置換（以後の元数）'});if(Object.hasOwn(op.directChanges||{},c)){const before=r.effectiveInitial??r.initial,n=op.directChanges[c];if(n!==before)out.push({type:'変更',category:label(c),text:show(before)+unit(c)+'→'+show(n)+unit(c)});}}
for(const r of order(p.records)){const n=op.corrections[r.code];if(Object.hasOwn(op.corrections,r.code)&&n!==r.initial)out.push({type:'元の予定訂正',category:label(r.code),text:show(r.initial)+unit(r.code)+'→'+show(n)+unit(r.code)});}
for(const code of Object.keys(ui.details))for(const row of ui.details[code]){if(row.changeFrom)out.push({type:'変更',category:label(code),treeChange:{before:{cut:row.changeFrom.cut,shape:cutShape(row.changeFrom.cut),species:names[row.changeFrom.species],diameter:sourceDiameter(row.changeFrom.size),count:row.count},after:row.targetNone===true?{none:true}:{cut:row.targetCut||(code[0]==='N'?'根':'枝'),shape:cutShape(row.targetCut||(code[0]==='N'?'根':'枝')),species:names[row.species],diameter:row.diameter,count:row.count}}});else if(row.kind==='changed')out.push({type:'変更（旧記録）',category:label(row.oldCode||code),text:'旧内訳を保持：'+show(row.oldDiameter)+'→'+show(row.diameter)+' / '+show(row.count)+'本'});}
for(const r of order(p.records)){if(!(r.additional>0))continue;const tree=/^[EN]/.test(r.code),items=tree?additionalDetails(p,r):[];out.push({type:'追加',category:label(r.code),count:r.additional,unit:unit(r.code),items,missing:tree?Math.max(0,r.additional-items.reduce((a,b)=>a+b.count,0)):0,auto:tree&&(ui.details?.[r.code]||[]).some(x=>x.kind==='added'&&!x.changeFrom&&x.allocationGenerated),...(r.code==='SB'?additionalBushDimensions(p,r):{dimensions:''})});}
return out;}
