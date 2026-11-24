import {requestedWaiting} from '../assistant/survey-waiting.mjs';
import {imageInput} from './image-input.mjs?v=bounded1';

export function addition(text,awaiting){
  const query=text.normalize('NFKC').trim().replace(/[。!！]+$/u,'')
    .replace(/(?:を)?追加(?:してください|してほしい|したい|して|する|で)?$/u,'').trim();
  const crown=query.match(/^(.+?)の(?:現調|現場調査)待ち(?:の(?:案件|現場|径間))?(?:を?(?:全部|全件))?$/u);
  const waiting=crown?requestedWaiting(crown[1]):requestedWaiting(query);
  if(waiting&&(awaiting||crown||waiting.scope==='all'))return {waiting};
  const parts=query.replace(/^管理番号[：:\s]*/u,'').split(/[、,\s]+/u).filter(Boolean);
  if(parts.length&&parts.every(n=>/^\d{8}$/.test(n)))return {managementNumbers:parts};
  const identifiers=query.replace(/^(?:径間|追加)[:：]\s*/u,'').split(/[、,\s]+/u).filter(Boolean);
  if(identifiers.length&&identifiers.every(s=>/^\d{8}$/.test(s)||/^[\p{L}\dー・]+[~〜][\p{L}\dー・]+$/u.test(s))){
    return {identifiers:identifiers.map(s=>s.replace(/[~〜]/g,'～'))};
  }
}
export async function surveyFile(file){
  if(file.type.startsWith('image/'))return {image:await imageInput(file)};
  if(!/\.pdf$/i.test(file.name)||file.size>700000)throw Error('写真か700KB以下のPDFを選んでください。');
  if((await file.slice(0,5).text())!=='%PDF-')throw Error('PDFを読み取れません。');
  const data=await new Promise((resolve,reject)=>{const reader=new FileReader();reader.onload=()=>resolve(reader.result);reader.onerror=()=>reject(Error('ファイルを開けません。'));reader.readAsDataURL(file);});
  return {pdf:'data:application/pdf;base64,'+data.split(',')[1]};
}
