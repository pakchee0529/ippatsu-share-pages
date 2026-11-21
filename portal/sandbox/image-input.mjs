export async function imageInput(file){
 if(!file)return undefined;
 if(file.size>25*1024*1024)throw Error('25MB以下の写真を選んでください');
 const bitmap=await createImageBitmap(file);
 try{
   const canvas=document.createElement('canvas');
   for(const size of [1500,1100,800]){
     const scale=Math.min(1,size/Math.max(bitmap.width,bitmap.height));
     canvas.width=Math.max(1,Math.round(bitmap.width*scale));canvas.height=Math.max(1,Math.round(bitmap.height*scale));
     const ctx=canvas.getContext('2d');ctx.fillStyle='white';ctx.fillRect(0,0,canvas.width,canvas.height);
     ctx.drawImage(bitmap,0,0,canvas.width,canvas.height);
     const data=canvas.toDataURL('image/jpeg',0.78);if(data.length<=1000000)return data;
   }
   throw Error('写真の範囲を絞ってください');
 }finally{bitmap.close();}
}
