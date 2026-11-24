import {validPhoto} from './attached-photo.mjs';

const selector='img[data-sandbox-generated-art]';
const allowedSlot=/^(hero|step-[1-4])$/;

export function artPlan(html){
  if(!html?.includes('data-sandbox-generated-art'))return [];
  const template=document.createElement('template');
  template.innerHTML=html;
  const plan=[...template.content.querySelectorAll(selector)].map(img=>({
    slot:img.getAttribute('data-sandbox-generated-art'),
    brief:img.getAttribute('data-art-brief')?.trim()
  }));
  if(plan.length>4||plan.some(({slot,brief})=>!allowedSlot.test(slot)||!brief||brief.length>700)||
    new Set(plan.map(item=>item.slot)).size!==plan.length)
    throw Error('手順と挿絵の対応を確認できません。');
  return plan;
}

export function artEntries(art){
  if(!art)return [];
  return Array.isArray(art)?art:[{slot:'hero',brief:art.brief,image:art.image}];
}

export function matchingArt(entries,{slot,brief}){
  return entries.find(item=>item?.slot===slot&&item.brief===brief&&validPhoto(item.image));
}

export function packArt(entries){
  if(entries.length===1&&entries[0].slot==='hero'){
    const {brief,image}=entries[0];
    return {brief,image};
  }
  return entries;
}

export function sameArt(left,right){
  const a=artEntries(left),b=artEntries(right);
  return a.length===b.length&&a.every(entry=>matchingArt(b,entry)?.image===entry.image);
}

export function displayArt(html,art){
  if(!art || !html.includes('data-sandbox-generated-art'))return html;
  const entries=artEntries(art).filter(item=>allowedSlot.test(item?.slot)&&typeof item.brief==='string'&&validPhoto(item.image));
  if(!entries.length)return html;
  const payload=JSON.stringify(entries).replaceAll('<','\\u003c');
  const binding=`<style>:where(img[data-sandbox-generated-art]){max-width:100%;height:auto}</style><script>(()=>{
    const selector='${selector}',entries=${payload};
    function apply(img){
      const found=entries.find(item=>img.getAttribute('data-sandbox-generated-art')===item.slot && img.getAttribute('data-art-brief')?.trim()===item.brief);
      if(found){img.removeAttribute('srcset');img.src=found.image;}
      else if(entries.some(item=>img.getAttribute('src')===item.image)){img.removeAttribute('src');}
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
