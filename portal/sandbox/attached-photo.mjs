const marker='img[data-sandbox-photo="attached"]';
const jpeg=/^data:image\/jpeg;base64,\/9j\/[A-Za-z0-9+/]*={0,2}$/;

export function usesAttachedPhoto(html){
  if(!html?.includes('data-sandbox-photo'))return false;
  const template=document.createElement('template');
  template.innerHTML=html;
  return Boolean(template.content.querySelector(marker));
}

export function validPhoto(value){
  return typeof value==='string'&&value.length<=320000&&jpeg.test(value);
}

export async function preparePhoto(value){
  if(validPhoto(value))return value;
  if(typeof value!=='string'||value.length>1000000||!jpeg.test(value))throw Error('添付写真をJPEGとして読み込めません。');
  const image=new Image();
  image.src=value;
  await image.decode();
  const canvas=document.createElement('canvas');
  for(const side of [1200,960,720,540]){
    const scale=Math.min(1,side/Math.max(image.naturalWidth,image.naturalHeight));
    canvas.width=Math.max(1,Math.round(image.naturalWidth*scale));
    canvas.height=Math.max(1,Math.round(image.naturalHeight*scale));
    canvas.getContext('2d').drawImage(image,0,0,canvas.width,canvas.height);
    const photo=canvas.toDataURL('image/jpeg',0.78);
    if(validPhoto(photo))return photo;
  }
  throw Error('掲載用の写真を準備できません。必要な範囲を切り抜いてください。');
}

// Only a bounded, validated JPEG is inserted into the fixed binding script.
export function displayPhoto(html,photo){
  if(!validPhoto(photo)||!html.includes('data-sandbox-photo'))return html;
  const setup=`<script>(()=>{
    const selector='img[data-sandbox-photo="attached"]',src="${photo}";
    function bind(el){
      if(el.matches(selector)){el.removeAttribute("srcset");el.src=src;}
      for(const img of el.querySelectorAll(selector)){img.removeAttribute("srcset");img.src=src;}
    }
    document.addEventListener("DOMContentLoaded",()=>{
      bind(document.documentElement);
      new MutationObserver(changes=>{
        for(const change of changes)for(const el of change.addedNodes)if(el.nodeType===1)bind(el);
      }).observe(document.documentElement,{childList:true,subtree:true});
    });
  })();<\/script>`;
  return setup+html;
}
