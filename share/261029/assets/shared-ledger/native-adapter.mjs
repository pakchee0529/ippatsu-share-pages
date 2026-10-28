import * as ops from './ledger-operations.mjs?v=20261028-origin-target21';
import {normalizeDesignNumber,normalizeDocumentDesign,setDocumentDesign} from './design-number.mjs?v=20261028-origin-target21';
import {normalizedSelection} from './special-summary.mjs?v=20261028-origin-target21';
// Pure translation: the normal v2 envelope, unknown fields and original quantities survive.
export const UI_SCHEMA='ippatsu-photo-ledger-ui/3';
export const codes=['E10','E20','E30','E40','E50','E60','N10','N20','N30','N40','N50','N60','SB','TK','TR'];
const clone=x=>JSON.parse(JSON.stringify(x)),number=n=>n===null||Number.isSafeInteger(n)&&n>=0&&n<=1000000;
export function projectUI(ui,base,caseId){
 if(ui?.schema!==UI_SCHEMA||ui.trialId!==caseId||ui.records?.length!==15)throw Error('新版入力の案件ID・保存形式が一致しません');
 if(ui.quantityOperations)ops.assertReady(ui);const rs=clone(ui.records);for(const [i,r] of rs.entries())if(r.code!==codes[i]||r.initial!==base[r.code]||!['unchanged','replace'].includes(r.mode)||![r.initial,r.revised,r.additional].every(number)||r.mode==='unchanged'&&r.revised!==null)throw Error(r.code+' の数量基準・変更追加を確認してください');
 if(ui.designNo!==undefined&&(typeof ui.designNo!=='string'||ui.designNo.length>100||/[\u0000-\u001f\u007f]/.test(ui.designNo)))throw Error('設計番号は100文字以内の文字列で入力してください');
 const seen=new Set(),confirmed=[],missing=[];for(const [i,p] of (ui.pairs?.SB||[]).entries()){const key=p.before?.no&&p.after?.no?p.before.date+':'+Number(p.before.no)+'|'+p.after.date+':'+Number(p.after.no):null;if(key&&seen.has(key))continue;if(key)seen.add(key);if(![p.width,p.height].every(number))throw Error('柴寸法は整数で保存してください');const active=p.before?.no||p.after?.no||p.width!==null||p.height!==null;if(!active)continue;if(p.width===null||p.height===null){missing.push(i+1);continue;}confirmed.push({width:p.width,height:p.height,area:p.width*p.height});}
 const sb=rs.find(x=>x.code==='SB'),area=confirmed.length?confirmed.reduce((n,p)=>n+p.area,0):null;
 if(!ui.quantityOperations){if(sb.mode==='replace'){sb.additional=area===null||sb.revised===null?null:Math.max(0,area-sb.revised);}else if(area!==null&&sb.initial===null){sb.mode='replace';sb.revised=area;sb.additional=null;}else if(area!==null){sb.mode=area<sb.initial?'replace':'unchanged';sb.revised=sb.mode==='replace'?area:null;sb.additional=Math.max(0,area-sb.initial);}else if((ui.pairs?.SB||[]).some(p=>p.before?.no||p.after?.no||p.width!==null||p.height!==null)){sb.mode='replace';sb.revised=null;sb.additional=null;}
 }
 if(area!==null&&area>1000000)throw Error('柴面積が保存範囲外です');if(ui.clearanceM!==null&&(!Number.isFinite(ui.clearanceM)||ui.clearanceM<0||ui.clearanceM>1000||Math.abs(ui.clearanceM*10-Math.round(ui.clearanceM*10))>1e-8))throw Error('保存済み離隔を確認してください');return {records:rs,clearanceM:ui.clearanceM,dimensions:confirmed,missingDimensions:missing};
}
export function fromNative(native,source,revision,seed){
 if(native)native=normalizeDocumentDesign(native);
 const base=source.planned;if(native&&(native.schema!=='ippatsu-photo-ledger/v2'||native.id!==source.case_id||native.case?.case_id!==source.case_id||Object.entries(base).some(([c,n])=>native.case.original_planned?.[c]!==n)))throw Error('保存済み台帳の案件・付託基準が一致しません。元データは保持しています');
 if(native?.ledger_ui_v3){const ui=clone(native.ledger_ui_v3);if(Object.hasOwn(ui,'designNo')&&ui.designNo!==(native.case?.design_no??''))throw Error('設計番号の保存値と入力欄が一致しません。会社の径間名・設計番号の修正で確認してください。');if(!Object.hasOwn(ui,'designNo'))ui.designNo=native.case?.design_no??'';if(!Object.hasOwn(ui,'clearanceM'))ui.clearanceM=native.clearanceM??null;if(!Array.isArray(ui.selected)){ui.selectionCompatibility={original:clone(ui.selected??null)};ui.selected=normalizedSelection(native,['BA',...codes,'US','DF','SL','HL','BV','RT','FR']);if(ui.selectionCompatibility.original!==false)ui.migrationWarnings=[...(ui.migrationWarnings||[]),'旧形式の選択状態を保存済み入力から復元しました。内容を確認してください'];}projectUI(ui,base,source.case_id);ui.revision=revision;return ops.ensureVineSlots(ui);}
 const ui=seed();ui.schema=UI_SCHEMA;ui.trialId=source.case_id;ui.revision=revision;ui.designNo=normalizeDesignNumber(source.design_no)??'';
 if(!native)return ui;
 ui.selected=normalizedSelection(native,['BA',...codes,'US','DF','SL','HL','BV','RT','FR']);if(!Array.isArray(native.selected)){ui.selectionCompatibility={original:clone(native.selected??null)};if(native.selected!==false)ui.migrationWarnings.push('旧形式の選択状態を保存済み入力から復元しました。内容を確認してください');}
 for(const r of ui.records){const n=native.case.planned?.[r.code];r.mode=n===base[r.code]?'unchanged':'replace';r.revised=r.mode==='replace'?n:null;const explicit=native.share_quantity_adjustments?.additional;if(Object.hasOwn(explicit||{},r.code))r.additional=explicit[r.code];else if(/^[EN]/.test(r.code))r.additional=Math.max(0,(native.cuts?.[r.code]||[]).reduce((n,p)=>n+p.count,0)-(n??0));}
 for(const c of ['BA','TK','TR','SB'])if(native.pairs?.[c]?.length)ui.pairs[c]=native.pairs[c].map((p,i)=>({...clone(p),id:p.id||c+'-saved-'+i,width:p.width??null,height:p.height??null}));
 for(const c of codes.filter(c=>/^[EN]/.test(c)))ui.cuts[c]=(native.cuts?.[c]||[]).map((r,i)=>({...clone(r),id:r.id||c+'-saved-'+i}));
 ui.special.US=(native.transport||[]).map((r,i)=>({...clone(r),id:r.id||'US-saved-'+i,vehicle:r.vehicle||(r.label?.includes('軽四輪')?'軽四輪':r.label?.includes('2t')?'2tダンプ':r.label?.replace(/^(指定場所運搬|運搬|運　搬　)\s*/,'').trim()||undefined)}));for(const r of native.special||[])if(ui.special[r.code])ui.special[r.code].push({...clone(r),id:r.id||r.code+'-saved-'+ui.special[r.code].length});
 ui.designNo=native.case?.design_no??'';ui.adjustments=clone(native.adjustments||[]);ui.clearanceM=native.clearanceM??null;
 // Explicit OFF remains OFF even when saved photo/dimension rows exist.
 ui.selected=[...new Set(ui.selected)];return ops.ensureVineSlots(ui);
}
export function toNative(ui,previous,source){
 const rawDesignNo=ui.designNo;ui=clone(ui);if(ui.designNo!==undefined)ui.designNo=normalizeDesignNumber(ui.designNo)??'';
 const projected=projectUI(ui,source.planned,source.case_id);let d=previous?clone(previous):{schema:'ippatsu-photo-ledger/v2',id:source.case_id,case:{...clone(source),original_planned:clone(source.planned)},selected:[],pairs:{},cuts:{},transport:[],special:[],adjustments:[]};
 d.case={...d.case,case_id:source.case_id,management_no:source.management_no,span_label:source.span_label,work_date:source.work_date,original_planned:{...d.case.original_planned,...clone(source.planned)},planned:clone(d.case.planned||source.planned)};
 d=setDocumentDesign(d,rawDesignNo===undefined?d.case.design_no:rawDesignNo);
 d.id=source.case_id;d.ledger_ui_v3=clone(ui);d.selected=clone(ui.selected);d.pairs={...d.pairs,...clone(ui.pairs)};d.cuts={...d.cuts,...clone(ui.cuts)};d.transport=clone(ui.special.US);d.special=Object.entries(ui.special).filter(([c])=>c!=='US').flatMap(([code,rows])=>rows.map(r=>({...clone(r),code}))).concat((previous?.special||[]).filter(r=>!Object.hasOwn(ui.special,r.code)));d.adjustments=clone(ui.adjustments);d.clearanceM=ui.clearanceM;
 for(const r of projected.records){const n=r.mode==='replace'?r.revised:r.initial;if(n!==null)d.case.planned[r.code]=n;}
 // Preserve the v2 envelope values for unknown UI quantities; the UI projection remains explicit null.
 d.share_quantity_adjustments={schema:'ippatsu-share-quantities/v1',case_id:source.case_id,base:clone(source.planned),additional:Object.fromEntries(projected.records.filter(r=>r.additional!==null).map(r=>[r.code,r.additional]))};
 return d;
}
