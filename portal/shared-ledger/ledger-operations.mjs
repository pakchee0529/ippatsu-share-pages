import {canonicalQuantity,computeKinds,checkBaseEdit,assertRawBasis,activeKinds} from './quantity-kinds.mjs?v=20261106-e20-independent-r1';
// Versioned explicit operations. Never infer/replay historical changes on read.
export const CUTS=['E','N'].flatMap(k=>[10,20,30,40,50,60].map(n=>k+n));
const clone=x=>JSON.parse(JSON.stringify(x)),base=r=>r.mode==='replace'?r.revised:r.initial;
const integer=n=>Number.isSafeInteger(n)&&n>=0&&n<=1000000;
const pureSum=rows=>(rows||[]).filter(x=>x.kind==='added'&&!x.changeFrom).reduce((n,x)=>n+(Number.isSafeInteger(x.count)?x.count:0),0);
const hasPhoto=r=>typeof r?.no==='string'&&r.no.trim()!=='';
export function sourceCode(cut,size){if(!['枝','芯','根'].includes(cut)||!/^\d{1,3}$/.test(String(size)))throw Error('元の切り方・サイズ(cm)を入力してください');const n=Number(size);if(n<1||n>999)throw Error('元サイズは1～999cmです');return (cut==='根'?'N':'E')+([10,20,30,40,50].find(x=>n<x)||60);}
// followup-002: record photo totals already entered before enabling, only where the current additional already equals photos-base (no silent change; null stays null).
function enabledPhotoTotals(d){const out={};for(const c of CUTS){const photos=d.cuts?.[c]||[];if(!photos.length||photos.some(x=>!integer(x.count)))continue;const r=d.records.find(x=>x.code===c),n=r&&base(r),total=photos.reduce((s,x)=>s+x.count,0);if(integer(n)&&r.additional===Math.max(0,total-n))out[c]=total;}return out;}
export function enable(d){if(!d.quantityOperations){const photoTotals=enabledPhotoTotals(d);d.quantityOperations={version:1,anchorRecords:clone(d.records),anchorDetails:clone(d.details),anchorPairs:clone(d.pairs),corrections:{},net:{},none:{},undoNone:{}};if(Object.keys(photoTotals).length)d.quantityOperations.photoTotals=photoTotals;}if(d.quantityOperations.version!==1)throw Error('数量操作の版を確認してください');return d.quantityOperations;}
export function correct(d,code,value){const o=enable(d);if(value!==null&&!integer(value))throw Error('予定訂正は0以上の整数です');o.corrections[code]=value;return refresh(d);}
export function toggleChange(d,code,index){enable(d);const row=d.details[code][index];if(row.changeFrom)delete row.changeFrom;else row.changeFrom={cut:'',size:'',species:''};return refresh(d);}
export function setTargetNone(d,code,index,on){enable(d);const row=d.details[code][index];if(!row?.changeFrom)throw Error('施工変更の行ではありません');if(on){row.targetNone=true;row.diameter='';delete row.targetCut;}else delete row.targetNone;return refresh(d);}
/** 純減（変更先なし）: 元切り方・サイズ・本数を元区分に記録。写真不要。実績(additional/photoTotals)は減算しない。 */
export function addPureDecrease(d,{cut,size,species,count}={}){
  enable(d);
  if(!species||!SPECIES_OK(species))throw Error('減らす変更の樹種を選択してください');
  if(!integer(count)||count<1)throw Error('減らす本数は1以上の整数です');
  const code=sourceCode(cut,size);
  d.details[code]??=[];
  d.details[code].push({
    id:'decrease-'+Date.now().toString(36)+Math.random().toString(36).slice(2,7),
    kind:'added',
    changeFrom:{cut,size:String(size),species},
    targetNone:true,
    diameter:'',
    oldDiameter:'',
    count,
    species:'',
    photoIds:[],
    pureDecrease:true
  });
  return refresh(d);
}
function SPECIES_OK(s){return typeof s==='string'&&['広葉樹','杉','桧','松','槙','梅','柿'].includes(s);}
/*060-UPDATE-PURE-DECREASE*/
export function updatePureDecrease(d,code,index,{cut,size,species,count}={}){enable(d);const row=d.details[code]?.[index];if(!row?.changeFrom||row.targetNone!==true)throw Error('減らす変更の行ではありません');if(species!==undefined){if(species!==''&&!SPECIES_OK(species))throw Error('減らす変更の樹種を選択してください');row.changeFrom.species=species;}if(cut!==undefined||size!==undefined){const nextCut=cut!==undefined?cut:row.changeFrom.cut;const nextSize=size!==undefined?String(size):String(row.changeFrom.size);const nextCode=sourceCode(nextCut,nextSize);row.changeFrom.cut=nextCut;row.changeFrom.size=nextSize;if(nextCode!==code){d.details[code].splice(index,1);d.details[nextCode]??=[];d.details[nextCode].push(row);}}if(count!==undefined){if(!integer(count)||count<1)throw Error('減らす本数は1以上の整数です');row.count=count;}if(row.oldDiameter===undefined)row.oldDiameter='';return refresh(d);}
export function removePureDecrease(d,code,index){
  enable(d);
  const row=d.details[code]?.[index];
  if(!row?.changeFrom||row.targetNone!==true)throw Error('減らす変更の行ではありません');
  d.details[code].splice(index,1);
  return refresh(d);
}
/** 元枠との残差（予定最終 vs 実績電卓）。減算を実績から再減算しない。 */
export function unmatchedDecreaseGap(d,code){
  const o=d?.quantityOperations;if(!o)return null;
  const r=d.records.find(x=>x.code===code);if(!r)return null;
  const plannedFinal=base(r);
  const captured=Object.hasOwn(o.photoTotals||{},code)?o.photoTotals[code]:null;
  if(!integer(plannedFinal)||!integer(captured))return {plannedFinal,captured,gap:null};
  return {plannedFinal,captured,gap:plannedFinal-captured};
}
export function setNet(d,code,values){if(!['TK','TR'].includes(code)||!Array.isArray(values)||values.some(x=>!Number.isSafeInteger(x)||Math.abs(x)>1000000))throw Error('増減は符号付き整数です');const o=enable(d);o.net[code]=clone(values);o.rawNet??={};o.rawNet[code]=values.join(',');return refresh(d);}
export function reduceVines(d,count){if(!integer(count))throw Error('つるの箇所数は整数です');const pairs=d.pairs.TR;if(count>=pairs.length)throw Error('末尾の空枠を減らす数を指定してください');if(pairs.slice(count).some(p=>hasPhoto(p.before)||hasPhoto(p.after)))throw Error('末尾に写真が残っています。途中の穴は撮忘です');const o=enable(d),r=o.anchorRecords.find(x=>x.code==='TR'),total=(Object.hasOwn(o.corrections,'TR')?o.corrections.TR:base(r))+(r.additional||0);d.pairs.TR=pairs.slice(0,count);if(!d.pairs.TR.length)d.pairs.TR=[{id:'TR-none',before:{date:'',no:''},after:{date:'',no:''},width:null,height:null}];o.net.TR=[count-total];if(o.extra)delete o.extra.TR;return refresh(d);}
function categoryRefs(d,c){return new Set((d.pairs[c]||[]).flatMap(p=>[p.before,p.after]).filter(hasPhoto).map(x=>x.date+':'+Number(x.no)));}
export function setNone(d,c){if(!['TK','TR','SB'].includes(c))throw Error('無しの対象が違います');if((d.pairs[c]||[]).some(p=>hasPhoto(p.before)&&hasPhoto(p.after)))throw Error(c+'：完成した前後ペアが残っています。無しを確定できません');const o=enable(d);if(o.none[c])return refresh(d);o.undoNone[c]={pairs:clone(d.pairs[c]),selected:d.selected.includes(c),correction:o.corrections[c],hasCorrection:Object.hasOwn(o.corrections,c),net:clone(o.net[c]||[]),raw:o.rawNet?.[c],extra:o.extra?.[c],hasExtra:Object.hasOwn(o.extra||{},c),adjustments:[]};/*060-SETNONE-SHARED-REFS*/const refs=categoryRefs(d,c);const cutRefs=CUTS.flatMap(code=>(d.cuts?.[code]||[]).filter(hasPhoto).map(x=>x.date+':'+Number(x.no)));const specialRefs=Object.values(d.special||{}).flat().flatMap(r=>(r.photos||[]).filter(hasPhoto).map(x=>x.date+':'+Number(x.no)));const others=new Set(['BA','TK','TR','SB'].filter(x=>x!==c).flatMap(x=>[...categoryRefs(d,x)]).concat(cutRefs,specialRefs));o.undoNone[c].adjustments=(d.adjustments||[]).filter(x=>refs.has(x.date+':'+Number(x.no))&&!others.has(x.date+':'+Number(x.no)));d.adjustments=(d.adjustments||[]).filter(x=>!o.undoNone[c].adjustments.includes(x));d.pairs[c]=[{id:c+'-none',before:{date:'',no:''},after:{date:'',no:''},width:null,height:null}];o.none[c]=true;o.corrections[c]=0;o.net[c]=[];o.rawNet??={};o.rawNet[c]='';if(o.extra)delete o.extra[c];d.selected=d.selected.filter(x=>x!==c);return refresh(d);}
export function undoNone(d,c){const o=enable(d),u=o.undoNone[c];if(!u)return refresh(d);d.pairs[c]=clone(u.pairs);d.adjustments.push(...clone(u.adjustments));if(u.selected&&!d.selected.includes(c))d.selected.push(c);if(u.hasCorrection)o.corrections[c]=u.correction;else delete o.corrections[c];o.net[c]=clone(u.net);o.rawNet??={};if(u.raw===undefined)delete o.rawNet[c];else o.rawNet[c]=u.raw;o.extra??={};if(u.hasExtra)o.extra[c]=u.extra;else delete o.extra[c];delete o.none[c];delete o.undoNone[c];return refresh(d);}

// calc-r2 / r10: 電卓/明示 additional 正本は内訳の追加・削除・編集で変えない（旧内訳削除の減算も、pureSum引き上げもしない）。photoTotals経路は下で上書き。
function pureTotal(anchor,_prior,_current){return anchor===null?null:anchor;}
// 旧式（互換判定専用）。保存値が旧計算と一致し新計算と違うときだけ legacy とみなす。
function legacyPureTotal(anchor,prior,current){if(anchor===null)return null;let removed=0;for(const old of prior||[]){if(old.kind!=='added'||old.changeFrom)continue;const now=(current||[]).find(x=>x.id===old.id);if(integer(old.count)){const kept=now&&!now.changeFrom&&integer(now.count)?Math.min(old.count,now.count):0;removed+=old.count-kept;}else if(now?.changeFrom&&integer(now.count))removed+=now.count;}return anchor-removed<0?anchor-removed:Math.max(anchor-removed,pureSum(current));}

function computeLegacy(d){const o=d.quantityOperations;if(!o)return {records:clone(d.records),errors:[],warnings:[]};if(o.version!==1)throw Error('数量操作版が違います');const rs=clone(o.anchorRecords),errors=[],warnings=[],out={},incoming={};const row=c=>rs.find(r=>r.code===c);let independentRawErrors=0;for(const [c,raw] of Object.entries(o.rawNet||{}))if(raw.trim()!==''&&raw.split(',').some(x=>!/^[-+]?\d+$/.test(x.trim()))){errors.push(c+'：増減の入力途中です。符号付き整数を完成してください');if(c==='TK'||c==='TR')independentRawErrors++;}
 for(const c of CUTS){out[c]=0;incoming[c]=0;}
 for(const [c,n] of Object.entries(o.corrections)){if(!row(c)){errors.push('訂正区分が不正');continue;}if(n===null)errors.push(c+'：予定訂正は未入力です。下書きを保持しています');if(n!==null&&!integer(n))errors.push(c+'：予定訂正は0以上整数');const r=row(c);r.mode=n===r.initial?'unchanged':'replace';r.revised=r.mode==='replace'?n:null;}
 for(const c of CUTS)for(const x of d.details[c]||[])if(x.changeFrom){let from;try{from=sourceCode(x.changeFrom.cut,x.changeFrom.size);}catch(e){errors.push(c+'：'+e.message);continue;}if(x.targetNone===true){if(!integer(x.count)||x.count<1){errors.push(c+'：変更先なしの本数を入力してください');continue;}if(from!==c||x.diameter!==''&&x.diameter!==undefined||x.targetCut){errors.push(c+'：変更先なしは元区分に記録し、変更先サイズを持てません');continue;}out[from]+=x.count;continue;}if(!integer(x.count)||x.count<1||!(x.diameter==='70+'||integer(x.diameter)&&x.diameter>0)){errors.push(c+'：変更先サイズと本数を入力してください');continue;}try{if(sourceCode(x.targetCut||(c[0]==='N'?'根':'枝'),x.diameter==='70+'?70:x.diameter)!==c)throw Error('区分違い');}catch{errors.push(c+'：変更先の切り方・径級を確認してください');continue;}out[from]+=x.count;incoming[c]+=x.count;}
 for(const c of CUTS){const r=row(c),n=base(r);if(out[c]&&(n===null||out[c]>n))errors.push(c+'：元枠が'+(n===null?'未確認':out[c]-n+'本不足'));const final=n===null?null:n-out[c]+incoming[c];if(final!==null&&(!integer(final)))errors.push(c+'：予定本数は0未満にできません');r.mode=final===r.initial?'unchanged':'replace';r.revised=r.mode==='replace'?final:null;const extra=(o.anchorRecords.find(x=>x.code===c).additional);r.additional=pureTotal(extra,o.anchorDetails[c],d.details[c]);if(Object.hasOwn(o.photoTotals||{},c)){const captured=o.photoTotals[c],photos=d.cuts[c]||[],actual=photos.reduce((n,x)=>n+(integer(x.count)?x.count:0),0);if(!integer(captured)||photos.some(x=>!integer(x.count)||x.count<1)||captured!==actual||final===null)errors.push(c+'：写真本数の根拠または基準が未確認です');else {r.additional=Math.max(0,captured-final);if(pureSum(d.details[c])>r.additional)errors.push(c+'：純追加内訳が追加必要数より'+(pureSum(d.details[c])-r.additional)+'本過剰です。手入力は保持しています');}}else if(r.additional!==null){const sum=pureSum(d.details[c]);if(sum>r.additional)errors.push(c+'：純追加内訳が追加必要数より'+(sum-r.additional)+'本過剰です。手入力は保持しています');else if(sum<r.additional)warnings.push(c+'：純追加内訳が追加必要数より'+(r.additional-sum)+'本不足です');}if(r.additional!==null&&!integer(r.additional))errors.push(c+'：純追加内訳が不整合');}
 // Capture validity before independent TK/TR/SB computations. Never infer dependencies from error text.
 // linked oldCode/oldCount changes are managed by input.mjs, not this legacy calculator.
 // Without that dependency proof, preserve the entire current cuts group.
 const hasLinkedChanges=Object.values(d.details||{}).some(rows=>rows.some(r=>r.kind==='changed'&&r.quantityLinked));
 const cutQuantitiesValid=errors.length===independentRawErrors&&!hasLinkedChanges;
 for(const c of ['TK','TR']){if(!Object.hasOwn(o.net,c))continue;const r=row(c),b=base(r),anchor=o.anchorRecords.find(x=>x.code===c);if(!integer(b)||!integer(anchor.additional)){errors.push(c+'：元数量が未確認');continue;}const net=o.net[c];if(!Array.isArray(net)||net.some(x=>!Number.isSafeInteger(x))) {errors.push(c+'：増減は整数');continue;}const total=b+anchor.additional+net.reduce((a,b)=>a+b,0);if(!integer(total)){errors.push(c+'：元枠不足（'+total+'）');continue;}const revised=Math.min(b,total);r.mode=revised===r.initial?'unchanged':'replace';r.revised=r.mode==='replace'?revised:null;r.additional=Math.max(0,total-b);}
 if(Object.hasOwn(o.extra||{},'TR')){if(!integer(o.extra.TR))errors.push('TR：追加箇所は未確認または整数以外です');else row('TR').additional=o.extra.TR;}
 for(const c of ['TK','TR','SB'])if(o.none[c]){if((d.pairs[c]||[]).some(p=>hasPhoto(p.before)||hasPhoto(p.after)||p.width!==null||p.height!==null)||d.selected.includes(c))errors.push(c+'：無しの数量と写真参照が一致しません');const r=row(c);r.mode='replace';r.revised=0;r.additional=0;}
 if(!o.none.SB){const active=(d.pairs.SB||[]).filter(p=>hasPhoto(p.before)||hasPhoto(p.after)||p.width!==null||p.height!==null);const dims=active.filter(p=>integer(p.width)&&integer(p.height));if(active.some(p=>!integer(p.width)||!integer(p.height)))errors.push('SB：寸法未入力を0にできません');if(dims.length){const total=dims.reduce((n,p)=>n+p.width*p.height,0),r=row('SB'),b=base(r),old=(o.anchorPairs.SB||[]).filter(p=>integer(p.width)&&integer(p.height));if(!integer(total))errors.push('SB：面積は整数の範囲内です');else {const revised=b===null?total:Math.min(b,total);r.mode=revised===r.initial?'unchanged':'replace';r.revised=r.mode==='replace'?revised:null;r.additional=b===null?0:Math.max(0,total-b);}}}
 const tr=d.pairs.TR||[];for(let i=0;i<tr.length-1;i++)if(!hasPhoto(tr[i].before)&&!hasPhoto(tr[i].after)&&tr.slice(i+1).some(p=>hasPhoto(p.before)||hasPhoto(p.after)))warnings.push('TR：'+(i+1)+'組目は撮忘です。自動で箇所を減らしません');
 // All cuts form one dependency group: transfers can affect both source and target.
 // Only errors emitted by the independent special-quantity computations leave it valid.
 return {records:rs,errors:[...new Set(errors)],warnings,cutQuantitiesValid};}
export function refresh(d){const p=compute(d);if(!p.errors.length){d.records=p.records;ensureVineSlots(d);}else if(p.cutQuantitiesValid===true){const cutRows=new Map(p.records.filter(r=>CUTS.includes(r.code)).map(r=>[r.code,r]));d.records=d.records.map(r=>cutRows.has(r.code)?cutRows.get(r.code):r);}return p;}
export function assertReady(d){const p=compute(d);if(p.errors.length)throw Error(p.errors.join(' ／ '));if(d.quantityOperations&&canonicalQuantity(p.records)!==canonicalQuantity(d.records))throw Error('数量操作と上部数量が一致しません。下書きを保持して再確認してください');return p;}
/** 旧L02互換: 保存additionalが旧pureTotalと一致し新計算と違う区分だけをlegacyと識別。明示0の新規入力は含めない。 */
export function detectLegacyQuantityMismatch(d){const o=d?.quantityOperations;if(!o)return [];const p=compute(d),out=[];for(const c of CUTS){if(Object.hasOwn(o.photoTotals||{},c))continue;const saved=d.records.find(r=>r.code===c)?.additional;const neu=p.records.find(r=>r.code===c)?.additional;const anchor=o.anchorRecords.find(x=>x.code===c)?.additional;const old=legacyPureTotal(anchor,o.anchorDetails?.[c],d.details?.[c]);if(saved===old&&saved!==neu)out.push({code:c,saved,computedNew:neu,computedOld:old,message:c+'：保存追加数'+saved+'は旧計算と一致し新計算（'+neu+'）と違います。表示は保存値を保持。保存・確定前に電卓/内訳を本人が直してください'});}return out;}
/** 旧追加数不一致に起因する純追加内訳の過不足だけを互換降格対象にする（訂正負数などは同bucketでも降格しない）。 */
function isLegacyAdditionalDetailError(e,code){return typeof e==='string'&&e.startsWith(code+'：')&&/純追加内訳が追加必要数/.test(e);}
/** 読取専用。保存値を壊さず、proven legacy追加不一致の内訳誤差だけ警告へ。他エラーは隠さない（保存はassertReady）。 */
export function assertReadable(d){const p=compute(d);const legacy=detectLegacyQuantityMismatch(d);const legacyCodes=new Set(legacy.map(x=>x.code));const kept=[],demoted=[];for(const e of p.errors){const m=/^([EN]\d{2}|SB|TK|TR)：/.exec(e);const code=m&&m[1];if(code&&legacyCodes.has(code)&&isLegacyAdditionalDetailError(e,code))demoted.push(e);else kept.push(e);}const warnings=[...p.warnings,...legacy.map(x=>x.message),...demoted.map(e=>'読取保持（旧計算不一致の区分）：'+e)];if(d.quantityOperations&&!kept.length&&!legacy.length&&canonicalQuantity(p.records)!==canonicalQuantity(d.records))warnings.push('数量操作の再計算と上部数量が一致しません。表示は保存値を保持しています');return {records:clone(d.records),errors:kept,warnings,legacy,readable:true,compute:p};}
export function photoTargets(d,c){const o=d?.quantityOperations;if(!o)return null;let original=Object.hasOwn(o.corrections,c)?o.corrections[c]:base(o.anchorRecords.find(x=>x.code===c)),changed=0;for(const code of CUTS)for(const row of d.details[code]||[])if(row.changeFrom&&integer(row.count)){let source;try{source=sourceCode(row.changeFrom.cut,row.changeFrom.size);}catch{continue;}if(source===c)original-=row.count;if(code===c&&row.targetNone!==true)changed+=row.count;}return {original,changed};}

export function ensureVineSlots(d){const r=d.records.find(x=>x.code==='TR'),n=base(r);if(n===null||r.additional===null)return d;const total=n+r.additional;if(!integer(total)||total>100)throw Error('TR：箇所数と最大100写真組を確認してください');const ids=new Set(Object.values(d.pairs).flat().map(p=>p.id));while(d.pairs.TR.length<total){let id='TR-slot-'+d.pairs.TR.length;while(ids.has(id))id+='x';ids.add(id);d.pairs.TR.push({id,before:{date:d.pairs.TR[0]?.before.date||'',no:''},after:{date:d.pairs.TR[0]?.after.date||'',no:''},width:null,height:null});}return d;}

export function setVineAdditional(d,n){const o=enable(d);o.extra??={};o.extra.TR=n;return refresh(d);}

/*060-RECONCILE-CLASSIFY*/
function outgoingFrom(d,code){let n=0;for(const c of CUTS)for(const row of d.details[c]||[]){if(!row.changeFrom||!integer(row.count))continue;let src;try{src=sourceCode(row.changeFrom.cut,row.changeFrom.size);}catch{return null;}if(src===code)n+=row.count;}return n;}
function diamOk(row){if(row.targetNone===true)return row.diameter===''||row.diameter===undefined;const d=row.diameter;if(d===''||d===undefined)return false;if(d==='70+')return true;const n=typeof d==='number'?d:Number(d);return Number.isSafeInteger(n)&&n>0;}
/** Stale rows valid vs original anchor plan (outgoing<=anchor base; rows structurally ok). */
function staleValidAgainstOriginal(d,code){
  const o=d.quantityOperations;if(!o)return false;
  const anchor=o.anchorRecords.find(x=>x.code===code);if(!anchor)return false;
  const base=anchor.mode==='replace'?anchor.revised:anchor.initial;
  if(!integer(base))return false;
  for(const c of CUTS)for(const row of d.details[c]||[]){
    if(!row.changeFrom)continue;
    let src;try{src=sourceCode(row.changeFrom.cut,row.changeFrom.size);}catch{return false;}
    if(src!==code)continue;
    if(!integer(row.count)||row.count<1)return false;
    if(!diamOk(row))return false;
  }
  const out=outgoingFrom(d,code);if(out===null)return false;
  return out<=base;
}
function correctionCausesShortage(d,code){
  const o=d.quantityOperations;if(!o||!Object.hasOwn(o.corrections,code))return false;
  const corrected=o.corrections[code];if(!integer(corrected))return false;
  const out=outgoingFrom(d,code);if(out===null)return false;
  return out>corrected&&staleValidAgainstOriginal(d,code);
}
export function isCorrectionStaleReconciliation(d,errors){
  const corr=d?.quantityOperations?.corrections||{};
  if(!errors?.length||!Object.keys(corr).length)return false;
  let any=false;
  for(const e of errors){
    const m=/^([EN]\d{2}|SB|TK|TR)：(元枠|予定本数)/.exec(e);
    if(!m)return false;
    if(!Object.hasOwn(corr,m[1]))return false;
    if(!correctionCausesShortage(d,m[1]))return false;
    any=true;
  }
  return any;
}
export function clearReconciliationDraft(d){if(d&&d.reconciliationDraft)delete d.reconciliationDraft;return d;}

function linkedSignature(details){return JSON.stringify(Object.entries(details||{}).flatMap(([code,rows])=>rows.filter(r=>r.kind==='changed'&&r.quantityLinked).map(r=>[code,r.id??null,r.oldCode??null,r.oldCount??null,r.count??null])).sort((a,b)=>JSON.stringify(a).localeCompare(JSON.stringify(b))));}
function validLinkedRow(code,r){
 const sizes=c=>{const n=Number(c.slice(1));return n===60?[...Array.from({length:11},(_,i)=>50+i*2),'70+']:Array.from({length:n===10?4:5},(_,i)=>(n===10?2:n-10)+i*2);};
 return CUTS.includes(code)&&CUTS.includes(r.oldCode)&&r.oldCode[0]===code[0]&&integer(r.oldCount)&&integer(r.count)&&SPECIES_OK(r.oldSpecies)&&SPECIES_OK(r.species)&&sizes(r.oldCode).includes(r.oldDiameter)&&sizes(code).includes(r.diameter);
}
export function assertCompleteLinkedChanges(d){
 if(Object.entries(d.details||{}).some(([code,rows])=>rows.some(r=>r.kind==='changed'&&r.quantityLinked&&!validLinkedRow(code,r))))throw Error('数量連動変更：旧変更内訳の区分・樹種・太さ・前後本数を完成してください。現在値は保持しています');
}
export function compute(d){
 // Apply the legacy editor's completeness requirements even when its saved
 // signature matches the anchor. Matching unfinished input is not completion.
 try{assertCompleteLinkedChanges(d);}catch(e){
  return {records:clone(d.records),errors:[e.message],warnings:[],cutQuantitiesValid:false};
 }
 // v5 linked changes predate operations. enable() snapshots their already-applied
 // records AND details together. Unchanged historical rows must not be replayed.
 // A different linked quantity after that snapshot is not a supported current UI operation.
 if(d.quantityOperations&&linkedSignature(d.details)!==linkedSignature(d.quantityOperations.anchorDetails)){
  return {records:clone(d.records),errors:['数量連動変更：取得時と旧変更内訳の数量が異なります。現在値を保持して整合確認を待っています'],warnings:[],cutQuantitiesValid:false};
 }
 return computeKinds(d,computeLegacy);
}

export function correctBase(d,c,n){enable(d);if(!checkBaseEdit(d,c,n))return refresh(d);const o=d.quantityOperations;const previous=Object.hasOwn(o.baseCorrections||{},c)?o.baseCorrections[c]:o.anchorRecords.find(x=>x.code===c).initial;o.baseCorrections??={};o.baseCorrections[c]=n;if(Number.isSafeInteger(n)){o.baseCorrectionHistory??=[];o.baseCorrectionHistory.push({kind:'instruction-base-correction',code:c,before:previous,after:n});}return refresh(d);}
export function directChange(d,c,n){enable(d);const next=clone(d);next.quantityOperations.directChanges??={};next.quantityOperations.directChanges[c]=n;const p=compute(next);if(p.errors.length&&n!==null)throw Error(p.errors.join(' ／ '));d.quantityOperations=next.quantityOperations;return refresh(d);}
export function assertDocumentQuantities(document){assertRawBasis(document);const ui=document.ledger_ui_v3;if(!activeKinds(ui))return;assertReady(ui);for(const r of ui.records){const n=r.mode==='replace'?r.revised:r.initial;if(document.case.planned[r.code]!==n||document.share_quantity_adjustments?.additional?.[r.code]!==r.additional||document.share_quantity_adjustments?.base?.[r.code]!==document.case.original_planned[r.code])throw Error(r.code+'：修正/変更の保存投影が一致しません');}}
export function reclassifyLegacyCorrections(ui,review){if(ui.trialId!==review.trialId||ui.revision!==review.revision)throw Error('移行対象のID/版が一致しません');const next=clone(ui),o=next.quantityOperations;for(const [c,t] of Object.entries(review.targets)){const a=o.anchorRecords.find(r=>r.code===c);if(a?.initial!==t.before||o.corrections[c]!==t.after)throw Error('移行前の値が一致しません');o.directChanges??={};o.directChanges[c]=t.after;delete o.corrections[c];}o.legacyReclassifications??=[];o.legacyReclassifications.push({kind:'explicit-correction-to-change',sourceRevision:review.revision,targets:clone(review.targets)});const p=compute(next);if(p.errors.length)throw Error(p.errors.join(' ／ '));next.records=p.records;return next;}

export function cancelDirectChange(d,c){const o=d.quantityOperations;if(!o||!Object.hasOwn(o.directChanges||{},c))return refresh(d);const next=clone(d),previous=next.quantityOperations.directChanges[c];delete next.quantityOperations.directChanges[c];const p=compute(next);if(p.errors.length)throw Error(p.errors.join(' ／ '));next.quantityOperations.directChangeCancellations??=[];next.quantityOperations.directChangeCancellations.push({kind:'cancel-direct-change',code:c,previousTarget:previous,sourceRevision:d.revision});d.quantityOperations=next.quantityOperations;return refresh(d);}
