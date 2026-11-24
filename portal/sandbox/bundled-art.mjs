const catalogue=new Map([
  ['raffle-drum','抽選器'],['field-kit','現場道具'],['trailhead','登山口'],['stopwatch','ストップウォッチ']
]);
const cached=new Map();
async function readArt(id){
  const artUrl=new URL('./art/'+id+'.webp',import.meta.url);
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
  const explicit=[...catalogue.keys()].filter(id=>html.includes(id));
  const ids=explicit.length?explicit:[...catalogue.keys()];
  return Promise.all(ids.map(async id=>{
    if(!cached.has(id))cached.set(id,readArt(id).catch(()=>{cached.delete(id);return '';}));
    return [id,{src:await cached.get(id),alt:catalogue.get(id)}];
  })).then(entries=>`<style>:where(img[data-sandbox-art]){max-width:100%;height:auto}</style><script>(()=>{
    const selector='img[data-sandbox-art]',art=new Map(${JSON.stringify(entries)}),bound=new WeakMap();
    function apply(img){
      const asset=art.get(img.dataset.sandboxArt);
      if(!asset||bound.has(img))return;
      bound.set(img,asset);
      if(!img.alt)img.alt=asset.alt;
      img.removeAttribute('srcset');
      if(asset.src){
        img.addEventListener('error',()=>{if(img.getAttribute('src')===asset.src)img.removeAttribute('src');},{once:true});
        img.src=asset.src;
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
          const old=bound.get(r.target);
          if(old){
            bound.delete(r.target);
            if(r.target.getAttribute('src')===old.src)r.target.removeAttribute('src');
            if(r.target.alt===old.alt)r.target.removeAttribute('alt');
          }
          bind(r.target);
        }
        else r.addedNodes.forEach(bind);
      }}).observe(document.documentElement,{childList:true,subtree:true,attributes:true,attributeFilter:['data-sandbox-art']});
    });
  })();<\/script>`);
}
