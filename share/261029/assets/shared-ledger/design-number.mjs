// Approved notation only; no recency or authority inference.
const clone=x=>JSON.parse(JSON.stringify(x));
export function normalizeDesignNumber(value){
 if(value===null||value===undefined)return null;
 if(typeof value!=='string')throw Error('設計番号は文字列で入力してください。');
 const text=value.replace(/[ \u3000]/g,'');if(text==='')return null;
 if(/\s/.test(text)||!/^B?[0-9]{4}$/.test(text))throw Error('設計番号は先頭B（任意）と半角数字4桁です。桁や文字を推測しません。');
 return text.startsWith('B')?text.slice(1):text;
}
export function documentDesignNumber(d){
 const value=normalizeDesignNumber(d?.case?.design_no),ui=d?.ledger_ui_v3;
 if(ui&&Object.hasOwn(ui,'designNo')&&normalizeDesignNumber(ui.designNo)!==value)throw Error('設計番号の実番号が一致しません。出典を確認してください。');
 if(value===null&&(d?.case?.design_number_forms||[]).some(v=>typeof v==='string'&&v.replace(/[ \u3000]/g,'')!==''))throw Error('空欄では既存番号を取り消しません。');
 return value;
}
function remember(c,raws){
 const forms=clone(c.design_number_forms||[]);if(!Array.isArray(forms)||forms.some(v=>typeof v!=='string'))throw Error('設計番号の原表記履歴を確認してください。');
 for(const raw of raws){if(typeof raw!=='string'||raw.replace(/[ \u3000]/g,'')==='')continue;let canonical=null;try{canonical=normalizeDesignNumber(raw);}catch{}if(raw!==canonical&&!forms.includes(raw))forms.push(raw);}
 if(forms.length)c.design_number_forms=forms;
}
export function normalizeDocumentDesign(d){
 const value=documentDesignNumber(d),out=clone(d),c=out.case??={},ui=out.ledger_ui_v3;
 remember(c,[c.design_no,ui?.designNo]);if(value!==null||Object.hasOwn(c,'design_no'))c.design_no=value??'';
 if(ui&&Object.hasOwn(ui,'designNo'))ui.designNo=value??'';return out;
}
export function setDocumentDesign(d,raw){
 const value=normalizeDesignNumber(raw),old=d.case||{},prior=[old.design_no,d.ledger_ui_v3?.designNo];
 if(value===null&&[...prior,...(old.design_number_forms||[])].some(v=>typeof v==='string'&&v.replace(/[ \u3000]/g,'')!==''))throw Error('空欄では既存番号を取り消しません。');
 const out=clone(d),c=out.case??={};remember(c,[...prior,raw]);c.design_no=value??'';
 if(out.ledger_ui_v3)out.ledger_ui_v3.designNo=value??'';return out;
}
