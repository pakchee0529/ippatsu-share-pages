export function localInstruction(text){
 const rename=text.trim().match(/^[「『](.+?)[」』](?:の(?:文字|表示|文言))?を[「『]([^「」『』]{1,80})[」』]に(?:して|変更して|変えて)[。！!]?$/u);
 if(rename)return {target:rename[1],property:'text',value:rename[2]};
 const size=text.trim().match(/^(.+?)(?:の文字|の数字)?を(?:もう少し|もっと)?(大き|小さ)(?:く|めに|め)?(?:表示)?(?:に)?(?:して|する)?[。！!]?$/u);
 if(size)return {target:size[1].replace(/^[「『]|[」』]$/g,''),property:'size',delta:size[2]==='大き'?6:-4};
}
export function matchesTarget(nodes,target){
 const all=Array.from(nodes);
 const exact=all.filter(e=>e.textContent.trim()===target);
 if(exact.length)return exact;
 return all.filter(e=>target==='タイトル'?e.matches('h1'):target==='見出し'?e.matches('h1,h2,h3'):target==='ボタン'?e.matches('button'):false);
}
export function fontSize(el){
 return Math.max(12,Math.min(48,parseFloat(el.style.fontSize)|| (el.isConnected&&el.ownerDocument===document?parseFloat(getComputedStyle(el).fontSize):0)||16));
}
