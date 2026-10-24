// Optional equipment measurements live in existing ledger JSON rows.
export const equipmentSpec = c => ({BV:{field:'heightM',unit:'m',label:'高所作業車の高さ'},RT:{field:'capacityT',unit:'t',label:'ラフターの容量'}})[c];
export function validMeasurement(value){return value===undefined||value===null||typeof value==='number'&&Number.isFinite(value)&&value>=0;}
const own=(o,k)=>o!=null&&Object.hasOwn(o,k);
function choice(document,code){
 for(const source of [document?.ledger_ui_v3,document]){
  if(!source||!own(source,'selected'))continue;
  const value=source.selected;
  if(value===false)return false;
  if(Array.isArray(value))return value.includes(code);
  if(value&&typeof value==='object'&&own(value,code)&&typeof value[code]==='boolean')return value[code];
 }
 return undefined;
}
export function sectionActive(document,code){
 if(!document)return false;
 const explicit=choice(document,code);if(explicit!==undefined)return explicit;
 // Missing selection is not equivalent to OFF or all ON. Recover actual input only.
 const ui=document.ledger_ui_v3||document,hasRef=r=>Boolean(r?.no);
 if((ui.cuts?.[code]||document.cuts?.[code]||[]).some(r=>hasRef(r)||Number(r.count)>0))return true;
 if((ui.pairs?.[code]||document.pairs?.[code]||[]).some(p=>hasRef(p.before)||hasRef(p.after)||p.width!==null&&p.width!==undefined||p.height!==null&&p.height!==undefined))return true;
 const record=ui.records?.find(r=>r.code===code);
 if(record&&(record.mode==='replace'||Number(record.additional)>0))return true;
 if(own(document.case?.planned,code)&&own(document.case?.original_planned,code)&&document.case.planned[code]!==document.case.original_planned[code])return true;
 const rows=ui.special?.[code]||(document.special||[]).filter(r=>r.code===code);
 const equipment=equipmentSpec(code);
 // Non-transport rows are only created by explicit section input. Keep legacy
 // expense/free-text rows visible even before photos, unless explicitly OFF.
 if(code!=='US'&&rows.length)return true;
 if(rows.some(r=>(r.photos||[]).some(hasRef)||equipment&&r[equipment.field]!==null&&r[equipment.field]!==undefined))return true;
 if(code==='US'&&(document.transport||[]).some(r=>(r.photos||[]).some(hasRef)))return true;
 if(code==='BA'&&ui.clearanceM!==null&&ui.clearanceM!==undefined)return true;
 return false;
}
export function normalizedSelection(document,codes){return codes.filter(code=>sectionActive(document,code));}
export function specialSummary(document){
 if(!document)return '';
 const ui=document.ledger_ui_v3;
 const rows=ui?Object.entries(ui.special||{}).flatMap(([code,items])=>items.map(row=>({...row,code}))):[...(document.special||[]),...(document.transport||[]).map(row=>({...row,code:'US'}))];
 return rows.filter(row=>sectionActive(document,row.code)).map(row=>{const spec=equipmentSpec(row.code);return (row.label||row.code)+(spec?' '+(row[spec.field]===null||row[spec.field]===undefined?'未入力':row[spec.field])+spec.unit:'');}).join(' ／ ');
}
