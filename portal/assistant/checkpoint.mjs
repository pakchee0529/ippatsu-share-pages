export function packCheckpoint(state){
 const assets=[];
 const body=JSON.stringify(state,(key,value)=>{
   if(typeof value!=='string'||!['pdf','image'].includes(key)||!value.startsWith('data:'))return value;
   let index=assets.indexOf(value);
   if(index<0)index=assets.push(value)-1;
   return {attachmentIndex:index};
 });
 return '{"assets":'+JSON.stringify(assets)+',"body":'+body+'}';
}
export function unpackCheckpoint(raw){
 const data=JSON.parse(raw);
 if(!Array.isArray(data?.assets)||!data.body)return data;
 function restore(obj){
   for(const [key,val] of Object.entries(obj)){
     if(['pdf','image'].includes(key)&&Number.isInteger(val?.attachmentIndex))obj[key]=data.assets[val.attachmentIndex];
     else if(val&&typeof val==='object')restore(val);
   }
 }
 restore(data.body);return data.body;
}
