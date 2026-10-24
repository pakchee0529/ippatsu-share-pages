export const CATEGORIES = [
  ...['branch','root'].flatMap((kind)=>['lt10','10_20','20_30','30_40','40_50','ge50'].map((band,i)=>({
    id:`${kind}_${band}`,label:`${kind==='branch'?'枝切':'根切'} ${['10cm未満','10〜20cm未満','20〜30cm未満','30〜40cm未満','40〜50cm未満','50cm以上'][i]}`,unit:'本',kind}))),
  {id:'bamboo',label:'竹伐採',unit:'本',kind:'other'},
  {id:'vine',label:'つる伐採',unit:'箇所',kind:'other'},
  {id:'bush',label:'柴伐採',unit:'m²',kind:'other'}];
export const KEY='clearance-candidate:v1:synthetic';
export const copy=(value)=>JSON.parse(JSON.stringify(value));
export const uid=()=>globalThis.crypto?.randomUUID?.() ?? `op-${Date.now()}-${Math.random().toString(16).slice(2)}`;
const fail=(message)=>{throw new Error(message);};
const finite=(v)=>v===null || (typeof v==='number'&&Number.isFinite(v)&&v>=0&&v<=1e9);
const text=(v,max=500)=>typeof v==='string'&&v.length<=max;
export const blankDimensions=()=>({raw:'',first:null,second:null,lengthUnit:'unconfirmed',axisOrder:'unconfirmed'});
export function parseDimensionRaw(raw){
  const m=raw.trim().match(/^(\d+(?:\.\d+)?)\s*[xX×*]\s*(\d+(?:\.\d+)?)$/);
  return m?{first:Number(m[1]),second:Number(m[2])}:{first:null,second:null};
}
export function dimensionView(d=blankDimensions()){
  const known=d.first!==null&&d.second!==null;
  return {width:d.axisOrder==='width_height'?d.first:d.axisOrder==='height_width'?d.second:null,
    height:d.axisOrder==='width_height'?d.second:d.axisOrder==='height_width'?d.first:null,
    areaCandidateM2:!known||d.lengthUnit==='unconfirmed'||d.axisOrder==='unconfirmed'?null:d.first*d.second*(d.lengthUnit==='cm'?0.0001:1)};
}
export function base(q){return q.mode==='replace'?q.revised:q.initial;}
export function quantity(q){const b=base(q);return b===null||q.additional===null?null:b+q.additional;}
export function changeDelta(q){return q.initial===null||q.mode==='replace'&&q.revised===null?null:base(q)-q.initial;}
export function parseSizes(raw){
  if(!raw.trim())return [];
  return raw.split('/').map(token=>{const m=token.trim().match(/^(\d+(?:\.\d+)?)(?:-(\d+))?$/);
    if(!m)fail('サイズ内訳は20-2/24-1/28の形式です。28だけの本数は未確認のまま保持します。');
    const diameterCm=Number(m[1]),count=m[2]===undefined?null:Number(m[2]);
    if(!finite(diameterCm)||!finite(count)||count!==null&&!Number.isSafeInteger(count))fail('サイズ内訳が範囲外です。');
    return {diameterCm,count};});
}
