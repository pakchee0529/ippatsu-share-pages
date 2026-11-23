// Read common camera image headers without decoding the pixel buffer.
async function dimensions(file){
 const bytes=new Uint8Array(await file.slice(0,256*1024).arrayBuffer());
 const view=new DataView(bytes.buffer);
 if(bytes.length>=24 && view.getUint32(0)===0x89504e47 && view.getUint32(12)===0x49484452)
   return [view.getUint32(16),view.getUint32(20)];
 if(bytes[0]!==255 || bytes[1]!==216)return;
 for(let i=2;i+4<bytes.length;){
   if(bytes[i++]!==255)return;
   while(bytes[i]===255)i++;
   const marker=bytes[i++];
   if(marker===0xda || marker===0xd9 || i+2>bytes.length)return;
   const length=view.getUint16(i);
   if(length<2 || i+length>bytes.length)return;
   if([192,193,194,195,197,198,199,201,202,203,205,206,207].includes(marker) && length>=8)
     return [view.getUint16(i+5),view.getUint16(i+3)];
   i+=length;
 }
}

export async function imageInput(file){
 if(!file)return undefined;
 if(file.size>25*1024*1024)throw Error('25MB以下の写真を選んでください');
 const size=await dimensions(file);
 // Supply one bound so the decoder keeps the aspect ratio and applies camera rotation.
 const options=size && Math.min(...size)>1500?{resizeWidth:1500,resizeQuality:'high'}:{};
 let bitmap;
 try{bitmap=await createImageBitmap(file,options);}
 catch{throw Error('写真を開けませんでした。写真アプリでJPEGに保存するか、紙の部分を切り抜いて送ってください。');}
 const canvas=document.createElement('canvas');
 try{
   for(const limit of [1500,1100,800]){
     const scale=Math.min(1,limit/Math.max(bitmap.width,bitmap.height));
     canvas.width=Math.max(1,Math.round(bitmap.width*scale));canvas.height=Math.max(1,Math.round(bitmap.height*scale));
     const ctx=canvas.getContext('2d');if(!ctx)throw Error('写真を縮小できません。紙の部分を切り抜いて送ってください。');
     ctx.fillStyle='white';ctx.fillRect(0,0,canvas.width,canvas.height);
     ctx.drawImage(bitmap,0,0,canvas.width,canvas.height);
     const blob=await new Promise(resolve=>canvas.toBlob(resolve,'image/jpeg',0.78));
     if(blob && 23+4*Math.ceil(blob.size/3)<=1000000){
       return await new Promise((resolve,reject)=>{const reader=new FileReader();reader.onload=()=>resolve(reader.result);reader.onerror=()=>reject(Error('写真を読み込めませんでした'));reader.readAsDataURL(blob);});
     }
   }
   throw Error('写真の範囲を絞ってください');
 }finally{bitmap.close();canvas.width=canvas.height=1;}
}
