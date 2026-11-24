import {validPhoto} from './attached-photo.mjs';

const selector='img[data-sandbox-generated-art="hero"]';

export function artBrief(html){
  if(!html?.includes('data-sandbox-generated-art'))return '';
  const template=document.createElement('template');
  template.innerHTML=html;
  const images=[...template.content.querySelectorAll(selector)];
  if(!images.length)return '';
  const brief=images[0].getAttribute('data-art-brief')?.trim();
  if(!brief || brief.length>700 || images.some(img=>img.getAttribute('data-art-brief')?.trim()!==brief))
    throw Error('生成する挿絵の説明を確認できません。');
  return brief;
}

export function matchesArt(art,brief){
  return Boolean(brief && art?.brief===brief && validPhoto(art.image));
}

export function displayArt(html,art){
  if(!art || !validPhoto(art.image) || typeof art.brief!=='string' || !html.includes('data-sandbox-generated-art'))return html;
  const brief=JSON.stringify(art.brief).replaceAll('<','\\u003c');
  const binding=`<style>:where(img[data-sandbox-generated-art]){max-width:100%;height:auto}</style><script>(()=>{
    const selector='${selector}',brief=${brief},src="${art.image}";
    function apply(img){
      if(img.matches(selector) && img.getAttribute('data-art-brief')?.trim()===brief){
        img.removeAttribute('srcset'); img.src=src;
      }else if(img.getAttribute('src')===src){img.removeAttribute('src');}
    }
    function bind(node){
      if(node.nodeType!==1)return;
      if(node.tagName==='IMG')apply(node);
      node.querySelectorAll(selector).forEach(apply);
    }
    document.addEventListener('DOMContentLoaded',()=>{
      bind(document.documentElement);
      new MutationObserver(changes=>{for(const r of changes){
        if(r.type==='attributes')apply(r.target);
        else r.addedNodes.forEach(bind);
      }}).observe(document.documentElement,{childList:true,subtree:true,attributes:true,attributeFilter:['data-art-brief','data-sandbox-generated-art']});
    });
  })();<\/script>`;
  return binding+html;
}
