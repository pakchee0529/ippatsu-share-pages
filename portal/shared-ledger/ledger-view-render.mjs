import {publicQuantityText} from './quantity-format.mjs?v=20261031-034-photo-list-r1';
const assetVersion=new URL(import.meta.url).searchParams.get('v')||'';
import {order,label,groups,show,unit,totalText,ledgerUI,workItems,clearanceText,designText} from './ledger-view-model.mjs?v=20261031-034-photo-list-r1';
import {historyText,total} from './read-model.mjs?v=20261031-034-photo-list-r1';
import {appendSummary} from './daily-render.mjs?v=20261031-034-photo-list-r1';
import {photoGridHTML,photoGridCSS} from './photo-grid.mjs?v=20261031-034-photo-list-r1';
import {printedPhotoGrid} from './print-order.mjs?v=20261031-034-photo-list-r1';
const el=(tag,text,cls)=>{const x=document.createElement(tag);if(text!==undefined)x.textContent=text;if(cls)x.className=cls;return x;};
const kinds=[['E','枝切り'],['N','根切り'],['TK','竹'],['TR','つる'],['SB','柴']];
function quantityTables(parent,p){const heading=el('h3',undefined,'quantity-heading');heading.append(el('span','伐採本数'),el('span','枝切り写真 '+(p.document?p.photos.branchCount+'枚':'—'),'branch-photo-count'));parent.append(heading);const table=el('table',undefined,'counts'),head=el('tr');for(const x of ['区分','10未満','10～20','20～30','30～40','40～50','50以上','計'])head.append(el('th',x));table.append(head);for(const [prefix,name] of kinds.slice(0,2)){const tr=el('tr'),rows=p.records.filter(r=>r.code[0]===prefix);tr.append(el('th',name));for(const r of rows){const cell=el('td'),parts=historyText(r).split('＋');for(const [i,text] of parts.entries())cell.append(el('span',(i?'＋':'')+text,'number-part'));tr.append(cell);}tr.append(el('td',totalText(rows),'total'));table.append(tr);}parent.append(table);const other=el('table',undefined,'other-counts'),h=el('tr');for(const x of ['区分','元','結果'])h.append(el('th',x));other.append(h);for(const [code,name] of kinds.slice(2)){const r=p.records.find(x=>x.code===code),tr=el('tr'),u=unit(code);tr.append(el('th',name),el('td',publicQuantityText(r.initial)+u),el('td',totalText([r])+u));other.append(tr);}parent.append(other);}
/** Display family only — strip size-band text from category. */
function activityFamily(category){const c=String(category||'');if(c.startsWith('枝切り'))return '枝切り';if(c.startsWith('根切り'))return '根切り';return c;}
/**
 * Render-only coalesce. Preserves groups(p) order; merges consecutive only.
 * 追加: consecutive same 枝切り|根切り family.
 * 変更/変更（旧記録）: ALL consecutive changes → one section (not by family).
 */
function coalesceActivityForDisplay(list){const out=[];for(const g of list||[]){const isAdd=g.type==='追加';const isChg=g.type==='変更'||g.type==='変更（旧記録）';const fam=activityFamily(g.category);const branchOrRoot=fam==='枝切り'||fam==='根切り';const prev=out[out.length-1];const canMergeAdd=prev&&isAdd&&prev.type==='追加'&&branchOrRoot&&activityFamily(prev.category)===fam;const canMergeChg=prev&&isChg&&(prev.type==='変更'||prev.type==='変更（旧記録）');if(canMergeAdd){prev.count=(prev.count||0)+(g.count||0);prev.items=[...(prev.items||[]),...(g.items||[])];prev.missing=(prev.missing||0)+(g.missing||0);prev.auto=prev.auto||g.auto;if(g.dimensions)prev.dimensions=g.dimensions;prev.unit=prev.unit||g.unit;prev.category=fam;continue;}if(canMergeChg){prev._rows=prev._rows||[prev._source||{...prev}];prev._rows.push({...g});prev.type='変更';prev.category='';continue;}const copy={...g,items:g.items?[...g.items]:g.items};if(isAdd&&branchOrRoot)copy.category=fam;if(isChg){copy.type='変更';copy.category='';copy._rows=[{...g}];copy._source={...g};}out.push(copy);}return out;}
function renderTreeChange(body,g){const box=el('div',undefined,'compact-summary');box.append(el('span','☆'));for(const [i,v] of [g.treeChange.before,g.treeChange.after].entries()){if(i)box.append(el('span','→'));if(v.none){box.append(el('span','0（変更先なし）'));continue;}const shape=v.shape||g.treeChange.shape,valid=(v.diameter==='70+'||Number.isFinite(v.diameter)&&v.diameter>0)&&Number.isSafeInteger(v.count)&&v.count>0;if(valid&&v.species&&['square','circle'].includes(shape)){appendSummary(box,[{kind:'tree',...v,shape}]);if(v.cut==='芯')box.append(el('span','（芯止め・CS枝換算）'));}else if(valid&&['枝','芯','根'].includes(v.cut)&&['square','circle'].includes(shape)){const mark=el('span',v.cut==='芯'?'芯止め':v.cut,'cut-mark cut-'+shape);mark.setAttribute('aria-label','変更元の切り方 '+(v.cut==='芯'?'芯止め（CS枝換算）':v.cut));box.append(mark,el('span',v.diameter+'-'+v.count));if(!i)box.append(el('span','（元樹種未確認）','missing'));}else box.append(el('span','未入力（?）'));}body.append(box);}
function activity(parent,p){const list=coalesceActivityForDisplay(groups(p));parent.append(el('h3','追加・変更・運搬'));if(!list.length){parent.append(el('p','—'));return;}const table=el('table',undefined,'activity');for(const g of list){const tr=el('tr'),heading=el('th'),body=el('td');heading.append(el('span',g.type,'kind'));if(g.category)heading.append(el('span',g.category));if(g.type==='追加'){body.append(el('strong','＋'+g.count+g.unit));if(g.items&&g.items.length){const box=el('div');appendSummary(box,g.items);body.append(box);}if(g.auto)body.append(el('p','自動配分・お任せの生成値を含む（実測値ではありません）','photo-help'));if(g.missing)body.append(el('p','樹種・実寸未記録（'+g.missing+'本の内訳）','missing'));}else if(g._rows){for(const row of g._rows){if(row.treeChange)renderTreeChange(body,row);else if(row.text)body.append(el('div',row.text));}}else if(g.treeChange){renderTreeChange(body,g);}else body.append(el('span',g.text));if(g.dimensions)body.append(el('p',g.dimensions+' m'));tr.append(heading,body);table.append(tr);}parent.append(table);}

const CSS='.cut-mark{display:inline-block;border:1px solid currentColor;padding:1px 4px;margin:0 3px}.cut-circle{border-radius:50%}.cut-square{border-radius:0}.ledger-view{background:white;border:1px solid #cbd5e1;border-radius:12px;padding:16px;margin:14px 0;min-width:0}.ledger-view h2{margin:0 0 6px;font-size:1.15rem}.ledger-view h3{font-size:1rem;margin:18px 0 8px}.ledger-view .quantity-heading{display:flex;flex-wrap:wrap;align-items:baseline;gap:4px 12px}.ledger-view .branch-photo-count{font-size:.82rem;font-weight:normal;color:#475569;white-space:nowrap}.ledger-view .meta{font-size:.82rem;color:#475569}.ledger-view table{border-collapse:collapse;width:100%;background:white;font-size:.86rem}.ledger-view th,.ledger-view td{border:1px solid #cbd5e1;padding:8px;vertical-align:top;overflow-wrap:anywhere}.ledger-view .counts{table-layout:fixed;font-size:.65rem}.ledger-view .counts th,.ledger-view .counts td{padding:3px;text-align:center}.ledger-view .counts th:first-child{width:42px}.ledger-view .counts th:last-child{width:44px}.ledger-view .number-part{display:block;white-space:nowrap}.ledger-view .other-counts{margin:12px 0}.ledger-view .total{white-space:normal}.ledger-view .activity th{width:34%;text-align:left}.ledger-view .activity th span{display:block}.ledger-view .kind{font-size:.75rem;color:#475569;margin-bottom:4px}.ledger-view .activity p{margin:4px 0 0}.ledger-view .missing{font-size:.82rem;color:#7c2d12}.ledger-view .activity td>strong{display:block;margin-bottom:4px}.ledger-view .nav{display:flex;flex-wrap:wrap;gap:8px;margin:10px 0 16px}.ledger-view .button{display:inline-flex;padding:9px 12px;border:1px solid #7dd3fc;border-radius:6px;background:#e0f2fe;text-decoration:none;color:#0755a1}.ledger-view .condition-summary th{width:30%;text-align:left}.ledger-view .condition-summary td{padding:6px 8px}.ledger-view .work-items{font-size:.85rem}.ledger-view .read-error{color:#7c2d12;border:1px solid #f59e0b;padding:8px}';
export function installViewStyles(doc=document){if(doc.querySelector('#normal-ledger-view-style'))return;const style=doc.createElement('style');style.id='normal-ledger-view-style';style.textContent=CSS+photoGridCSS;doc.head.append(style);}
export function renderProjection(parent,p,{mode,date,conditions,notes=[],mapLink}={}){installViewStyles(parent.ownerDocument);const section=el('article',undefined,'ledger-view');section.dataset.managementNo=p.entry.cs;const h=el('h2');if(mode==='daily'){const a=el('a',p.entry.label);a.href='../instructions/?management_no='+p.entry.cs;h.append(a);}else h.textContent=p.entry.label;section.append(h);const carried=p.document?.case?.work_date&&p.document.case.work_date!==date;const day=carried?date:(p.document?.case?.work_date||date);section.append(el('p',(carried?'予定日 ':'作業日 ')+('20'+day.slice(0,2)+'/'+day.slice(2,4)+'/'+day.slice(4)),'meta'));const nav=el('nav',undefined,'nav');if(mode==='daily'){const a=el('a','指示書','button');a.href='../instructions/?management_no='+p.entry.cs;nav.append(a);const input=el('a','台帳入力','button');input.href='../../../portal/shared-ledger/input.html?date='+date+'&management_no='+p.entry.cs+'&ui='+encodeURIComponent(assetVersion);nav.append(input);}if(mapLink){const a=el('a','地図を開く','button');a.href=mapLink;a.target='_blank';a.rel='noopener';nav.append(a);}if(nav.children.length)section.append(nav);if(conditions){conditions.classList.add('condition-summary');section.append(conditions);}for(const note of notes)section.append(note);if(p.error)section.append(el('p','保存情報を照合できないため、元の数量を表示しています。','read-error'));
 // Surface project/read diagnostics (legacy + unrelated errors) without replacing saved quantity tables.
 const diagParts=[p.message,...(p.readErrors||[]),...(p.readWarnings||[])].filter(x=>typeof x==='string'&&x.trim());
 const diag=[...new Set(diagParts)];
 if(diag.length){const status=el('p',diag.join(' '),(p.readErrors||[]).length||p.error?'read-error saved-ledger-status':'meta saved-ledger-status');status.setAttribute('role','status');status.dataset.readDiagnostic='1';section.append(status);}
 const design=el('p',undefined,'design-number');design.dataset.designNumber='saved';design.append(el('strong','設計番号：'),el('span',designText(p.document)));section.append(design);const clearance=el('p',undefined,'clearance');clearance.dataset.clearance='metres';clearance.append(el('strong','離隔：'),el('span',clearanceText(p.document)));section.append(clearance);quantityTables(section,p);activity(section,p);const items=workItems(p);if(items)section.append(el('p',items,'work-items'));if(mode==='instructions'&&p.document)photoAllocation(section,p);parent.append(section);return section;}

// Instruction-only photo references. Never changes saved rows or quantity logic.
const photoEscape = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const rawPhotoNo = ref => {
  const raw = ref?.no === null || ref?.no === undefined ? '' : String(ref.no);
  return /^\d{1,3}$/.test(raw) && Number(raw) > 0 ? raw : '?';
};
export function instructionPhotoPlan(document, records) {
  const ui = ledgerUI(document), result = [];
  if (!ui) return result;
  const selected = code => ui.selected?.includes(code);
  const pair = (code, name) => {
    if (!selected(code)) return;
    const rows = ui.pairs?.[code] || [];
    if (rows.length) result.push({code, name, kind:'pairs', rows});
  };
  pair('BA', '伐採前後');
  for (const record of order(records)) {
    if (!/^[EN](10|20|30|40|50|60)$/.test(record.code) || !selected(record.code)) continue;
    const rows = ui.cuts?.[record.code] || [];
    if (rows.length) result.push({code:record.code, name:label(record.code), kind:'cuts', rows, record});
  }
  pair('TK', '竹伐採前後'); pair('TR', 'つる伐採前後'); pair('SB', '柴伐採前後');
  const names = {US:'運搬',DF:'伐採実費',SL:'斜面木実費',HL:'吊り切り実費',BV:'高所作業車',RT:'ラフター',FR:'その他（自由記述）'};
  const codes = ['US','DF','SL','HL','BV','RT','FR'];
  for (const code of Object.keys(ui.special || {})) if (!codes.includes(code)) codes.push(code);
  for (const code of codes) {
    if (!selected(code)) continue;
    const sourceRows = ui.special?.[code] || [];
    const rows = sourceRows.flatMap(row => row.photos || []);
    if (sourceRows.length) result.push({code, name:names[code] || 'その他（'+code+'）', kind:'special', rows, sourceRows});
  }
  return result;
}
function preservedPhotoGrid(rows, {counts=false, claims=false}={}) {
  let html = '<section class="photo-sheet">';
  for (let i=0; i<rows.length; i+=8) {
    html += '<div class="photo-row">';
    for (const row of rows.slice(i,i+8)) {
      const no = rawPhotoNo(row), count = Number.isInteger(row.count) && row.count >= 0 ? row.count : null;
      const claim = row.quantityGroup==='changed' ? '変更' : row.claim==='PLANNED' ? '元' : row.claim==='ADDED' ? '追加' : '未確認';
      html += '<div class="photo-item" data-photo-no="'+photoEscape(no)+'" data-claim="'+photoEscape(row.claim||'')+'"><span class="photo-number">'+photoEscape(no)+'</span>';
      if (counts) html += '<span class="photo-count" aria-label="本数 '+(count===null?'未記録':count)+'">'+(count===null?'?':count)+'</span>';
      html += '<small class="photo-capture">'+photoEscape(row.date || '撮影日未設定')+'</small>';
      if (claims || row.claim==='ADDED' || row.quantityGroup==='changed') html += '<small class="photo-claim">'+claim+'</small>';
      html += '</div>';
    }
    html += '</div>';
  }
  return html+'</section>';
}
function photoAllocation(parent,p) {
  parent.append(el('h3','写真番号と本数'),el('p','使用写真を分類順に表示。前後はペアごとに前-後。? は番号未記録。兼用写真は用途ごとに表示します。','photo-help'));
  parent.append(el('style','.ledger-view .photo-pair{display:inline-block;border:1px solid #cbd5e1;border-radius:4px;padding:6px;margin:4px;min-width:110px}'));
  const ui = ledgerUI(p.document), plan = instructionPhotoPlan(p.document,p.records);
  for (const group of plan) {
    const box=el('section'); box.dataset.photoCategory=group.code;
    const field=group.code==='RT'?'capacityT':group.code==='BV'?'heightM':null;
    const measure=field?' '+group.sourceRows.map(row=>show(row[field])+(group.code==='RT'?'t':'m')).join('、'):'';
    box.append(el('h4',group.name+measure,'photo-topic'));
    const grid=el('div');
    if (group.kind==='pairs') {
      group.rows.forEach((pair,index)=>{
        const before=rawPhotoNo(pair.before), after=rawPhotoNo(pair.after);
        const row=el('p',undefined,'photo-pair');row.dataset.photoPair=group.code+':'+index;
        row.append(el('span',before+'-'+after,'photo-number'));
        row.append(el('small',(pair.before?.date||'前撮影日未設定')+' / '+(pair.after?.date||'後撮影日未設定'),'photo-capture'));
        if(before==='?'||after==='?')row.append(el('span','（'+(before==='?'?'前':'')+(before==='?'&&after==='?'?'・':'')+(after==='?'?'後':'')+'番号未設定）','missing'));
        grid.append(row);
      });
    } else if (group.kind==='cuts') {
      const r=group.record, target=r.mode==='replace'?r.revised:r.initial;
      const printed=printedPhotoGrid(group.rows,target,group.code,ui);
      grid.innerHTML=preservedPhotoGrid(printed.ordered,{counts:['E10','N10'].includes(group.code),claims:['E10','N10'].includes(group.code)});
      if(!printed.exact)box.append(el('p','元本数に一致する写真の組合せを確認してください','missing'));
    } else {
      grid.innerHTML=group.rows.length?preservedPhotoGrid(group.rows):'<p class="photo-help">写真番号未記録</p>';
    }
    box.append(grid);parent.append(box);
  }
  if(!plan.length)parent.append(el('p','写真番号未入力','photo-help'));
}
