const artUrl=new URL('./art/raffle-drum.webp',import.meta.url);
let cached;
async function readDrum(){
  const response=await fetch(artUrl,{mode:'same-origin',credentials:'omit',redirect:'error',signal:AbortSignal.timeout(4500)});
  if(!response.ok)throw Error('画像を取得できません');
  const bytes=await response.arrayBuffer();
  if(bytes.byteLength<12||bytes.byteLength>2*1024*1024)throw Error('画像のサイズを確認してください');
  const head=new Uint8Array(bytes,0,12);
  if(String.fromCharCode(...head.slice(0,4))!=='RIFF'||String.fromCharCode(...head.slice(8))!=='WEBP')throw Error('WebPを確認してください');
  return await new Promise((resolve,reject)=>{
    const reader=new FileReader();
    reader.onload=()=>resolve(reader.result);
    reader.onerror=()=>reject(Error('画像を読み込めません'));
    reader.readAsDataURL(new Blob([bytes],{type:'image/webp'}));
  });
}
export function bundledArt(html){
  if(!/data-sandbox-art|sandboxArt/.test(html))return null;
  cached??=readDrum().catch(()=>{cached=null;return '';});
  return cached.then(src=>`<style>:where(img[data-sandbox-art="raffle-drum"]){max-width:100%;height:auto}</style><script>(()=>{
    const selector='img[data-sandbox-art="raffle-drum"]',src=${JSON.stringify(src)},bound=new WeakSet();
    function apply(img){
      if(bound.has(img))return;
      bound.add(img);
      if(!img.alt)img.alt='抽選器';
      img.removeAttribute('srcset');
      if(src){
        img.addEventListener('error',()=>img.removeAttribute('src'),{once:true});
        img.src=src;
      }else img.removeAttribute('src');
    }
    function bind(node){
      if(node.nodeType!==1)return;
      if(node.matches(selector))apply(node);
      node.querySelectorAll(selector).forEach(apply);
    }
    document.addEventListener('DOMContentLoaded',()=>{
      bind(document.documentElement);
      new MutationObserver(records=>{for(const r of records){
        if(r.type==='attributes'){
          if(bound.delete(r.target)&&!r.target.matches(selector)&&r.target.getAttribute('src')===src)r.target.removeAttribute('src');
          bind(r.target);
        }
        else r.addedNodes.forEach(bind);
      }}).observe(document.documentElement,{childList:true,subtree:true,attributes:true,attributeFilter:['data-sandbox-art']});
    });
  })();<\/script>`);
}
