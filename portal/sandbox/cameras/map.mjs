import areas from './municipalities.mjs';

const namespace = 'http://www.w3.org/2000/svg';
const longitudeScale = Math.cos(34.16 * Math.PI / 180);
const artwork = {
  '五條市': {fill:'#c8d8bb',label:[135.710,34.345]},
  '大淀町': {fill:'#f0d8ab',label:[135.795,34.407]},
  '吉野町': {fill:'#dcc9a6',label:[135.919,34.391]},
  '十津川村': {fill:'#afcdc0',label:[135.696,34.019]}
};
const source = 'https://nlftp.mlit.go.jp/ksj/gml/datalist/KsjTmplt-N03-2026.html';
const projected = ([lng, lat]) => [(lng-135.7)*longitudeScale,34.2-lat];
function svg(tag, attributes={}, label){
  const element=document.createElementNS(namespace,tag);
  for(const [name,value] of Object.entries(attributes))element.setAttribute(name,String(value));
  if(label!==undefined)element.textContent=label;
  return element;
}
function button(label, action){
  const el=document.createElement('button');el.type='button';el.textContent=label;el.onclick=action;return el;
}
const regions=areas.map(area=>({...area,paths:area.rings.map(ring=>ring.map(projected))}));
const mounted=new WeakMap();
const css=`
.regional-map {--rm-ink:#173e37;--rm-line:#989f88;--rm-paper:#f7f3e7;--rm-water:#deede8;--rm-green:#275b4c;--rm-white:#fffdf4;--rm-focus:#b94d17;color:var(--rm-ink)}
.regional-map .rm-stage{position:relative;height:clamp(340px,61svh,560px);overflow:clip;border:1px solid var(--rm-line);border-radius:16px;background:var(--rm-paper)}
.rm-stage>svg{display:block;width:100%;height:100%;touch-action:none;user-select:none}
.rm-zoom{position:absolute;right:8px;top:8px;display:grid;gap:2px}
.regional-map .rm-zoom button,.regional-map .rm-picker button{color:var(--rm-ink);background:var(--rm-white);border:1px solid var(--rm-line);border-radius:8px;min-width:44px;min-height:44px;line-height:1.1;cursor:pointer;font:inherit}
.regional-map .rm-zoom button{padding:4px 8px;font-weight:700}
.rm-pin{cursor:pointer}.rm-pin:focus{outline:none}.rm-pin:focus-visible .rm-pin-ring{stroke:var(--rm-focus);stroke-width:4px}
.regional-map button:focus-visible,.regional-map a:focus-visible,.rm-stage>svg:focus-visible{outline:3px solid var(--rm-focus);outline-offset:-3px}
.rm-picker{display:flex;flex-wrap:wrap;gap:6px;align-items:center;padding:8px 0}
.rm-picker[hidden]{display:none}.rm-picker strong{flex-basis:100%}.regional-map .rm-picker button{padding:8px 12px}
.rm-credit{margin:5px 0 0;font-size:.75rem;color:var(--rm-ink)}.rm-credit a{color:inherit;text-decoration:underline;text-underline-offset:2px}
`;

export function renderMap(container,cameras,onPick){
  mounted.get(container)?.();
  if(!document.getElementById('regional-camera-map-styles')){
    const style=document.createElement('style');style.id='regional-camera-map-styles';style.textContent=css;document.head.append(style);
  }
  container.classList.add('regional-map');
  const stage=document.createElement('div');stage.className='rm-stage';
  const canvas=svg('svg',{tabindex:0,role:'group','aria-label':'地域のライブカメラ地図。矢印キーで移動、プラスとマイナスで拡大縮小できます。'});
  const toolbar=document.createElement('div');toolbar.className='rm-zoom';
  const chooser=document.createElement('div');chooser.className='rm-picker';chooser.hidden=true;
  const credit=document.createElement('p');credit.className='rm-credit';
  const attribution=document.createElement('a');attribution.href=source;attribution.target='_blank';attribution.rel='noopener';attribution.textContent='国土交通省「国土数値情報 行政区域（2026年）」';
  const license=document.createElement('a');license.href='https://creativecommons.org/licenses/by/4.0/deed.ja';license.target='_blank';license.rel='noopener';license.textContent='CC BY 4.0';
  credit.append('境界は',attribution,'を簡略化。',license);
  stage.append(canvas,toolbar);container.replaceChildren(stage,chooser,credit);
  const entries=[];
  for(const camera of cameras){
    if(camera.lat==null||camera.lng==null||camera.lat===''||camera.lng==='')continue;
    const lat=Number(camera.lat),lng=Number(camera.lng);
    if(Number.isFinite(lat)&&Number.isFinite(lng)&&Math.abs(lat)<=90&&Math.abs(lng)<=180)entries.push({camera,point:projected([lng,lat])});
  }
  const points=regions.flatMap(region=>region.paths.flat()).concat(entries.map(item=>item.point));
  const xs=points.map(p=>p[0]),ys=points.map(p=>p[1]);
  const bounds=[Math.min(...xs),Math.min(...ys),Math.max(...xs),Math.max(...ys)];
  const home=[(bounds[0]+bounds[2])/2,(bounds[1]+bounds[3])/2];
  let center=[...home], zoom=1, width, height, scale;
  const unique='map-'+Math.random().toString(36).slice(2);
  const paper=svg('pattern',{id:unique+'-grain',width:10,height:10,patternUnits:'userSpaceOnUse'});
  paper.append(svg('circle',{cx:2,cy:3,r:.7,fill:'#667a62',opacity:.24}));
  const woods=svg('pattern',{id:unique+'-woods',width:29,height:26,patternUnits:'userSpaceOnUse'});
  woods.append(svg('path',{d:'m5 13 2.5-4 2.5 4 m9 9 1.8-3 1.8 3',fill:'none',stroke:'#536f56',opacity:.20,'stroke-width':1.3}));
  const defs=svg('defs');defs.append(paper,woods);
  const terrain=svg('g',{'aria-hidden':true}),legend=svg('g',{'aria-hidden':true}),pins=svg('g');
  canvas.append(defs,svg('rect',{width:'100%',height:'100%',fill:'url(#'+unique+'-grain)'}),terrain,pins,legend);
  function screen(p){return [(p[0]-center[0])*scale+width/2,(p[1]-center[1])*scale+height/2];}
  function hideChoices(){chooser.hidden=true;chooser.replaceChildren();}
  function pick(group){
    hideChoices();
    if(group.items.length===1){onPick(group.items[0].camera);return;}
    const title=document.createElement('strong');title.textContent='この付近のカメラ（'+group.items.length+'台）';
    chooser.append(title);
    for(const item of group.items){
      chooser.append(button(item.camera.name,()=>onPick(item.camera)));
    }
    if(zoom<16)chooser.append(button('この付近を拡大',()=>{
      center=[...group.items[0].point];changeZoom(2);canvas.focus({preventScroll:true});
    }));
    chooser.hidden=false;
    chooser.querySelector('button').focus({preventScroll:true});
    chooser.scrollIntoView({block:'nearest'});
  }
  function pin(group){
    const count=group.items.length,label=count===1?group.items[0].camera.name:'この付近のカメラ '+count+'台';
    const pin=svg('g',{class:'rm-pin',transform:'translate('+group.x+' '+group.y+')',tabindex:0,role:'button','aria-label':label});
    pin.append(svg('title',{},label),svg('circle',{r:22,fill:'transparent'}));
    pin.append(svg('circle',{class:'rm-pin-ring',r:12.5,fill:'#235747',stroke:'#fffdf4','stroke-width':2}));
    pin.append(svg('path',{d:'M-7 -4h3l1.4-2h5L4-4h3v9H-7Z',fill:'#fffdf4','stroke-linejoin':'round'}),svg('circle',{cx:0,cy:.5,r:2.8,fill:'#235747'}));
    if(count>1){
      pin.append(svg('circle',{cx:10,cy:-9,r:7.7,fill:'#944c27',stroke:'#fffdf4','stroke-width':1}),svg('text',{x:10,y:-5.8,'text-anchor':'middle','font-size':9,'font-weight':700,fill:'#fffdf4'},count));
    }
    pin.onclick=e=>{e.stopPropagation();pick(group);};
    pin.onkeydown=e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();e.stopPropagation();pick(group);}};
    pins.append(pin);
  }
  function titleMark(name,coord,size,occupied){
    const [cx,cy]=screen(projected(coord));
    if(cx<0||cy<0||cx>width||cy>height)return;
    const half=name.length*size/2+3;
    for(const [dx,dy] of [[0,0],[0,-22],[0,25],[38,0],[-38,0],[40,-22],[-40,-22],[55,20],[-55,20],[0,45]]){
      const x=cx+dx,y=cy+dy;
      const b=[x-half,y-size,x+half,y+3];
      if(b[0]<2||b[1]<2||b[2]>width-2||b[3]>height-2||occupied.some(o=>b[0]<o[2]&&b[2]>o[0]&&b[1]<o[3]&&b[3]>o[1]))continue;
      if(dx||dy)terrain.append(svg('line',{x1:cx,y1:cy,x2:x,y2:y-size/2,stroke:'#7b8b74','stroke-width':1}));
      terrain.append(svg('text',{x,y,'text-anchor':'middle','font-size':size,'font-weight':700,fill:'#30483c',stroke:'#f5f2e4','stroke-width':3,'paint-order':'stroke', 'stroke-linejoin':'round'},name));
      occupied.push(b);break;
    }
  }
  function draw(){
    const box=stage.getBoundingClientRect();width=Math.max(1,box.width);height=Math.max(1,box.height);
    scale=zoom*Math.min(Math.max(5,width-44)/(bounds[2]-bounds[0]),Math.max(5,height-44)/(bounds[3]-bounds[1]));
    canvas.setAttribute('viewBox',`0 0 ${width} ${height}`);
    terrain.replaceChildren();legend.replaceChildren();pins.replaceChildren();
    for(const region of regions){
      const d=region.paths.map(ring=>ring.map((coord,i)=>{const [x,y]=screen(coord);return (i?'L':'M')+x.toFixed(1)+' '+y.toFixed(1);}).join('')+'Z').join('');
      terrain.append(svg('path',{d,fill:artwork[region.name].fill,'fill-rule':'evenodd',stroke:'#73836c','stroke-width':1.4,'stroke-linejoin':'round'}),svg('path',{d,fill:'url(#'+unique+'-woods)','fill-rule':'evenodd'}));
    }
    const groups=[];
    for(const item of entries){
      const [x,y]=screen(item.point);
      if(x < -15 || x > width+15 || y < -15 || y > height+15)continue;
      const near=groups.find(g=>Math.hypot(g.x-x,g.y-y)<44);
      if(near)near.items.push(item);else groups.push({x,y,items:[item]});
    }
    const occupied=groups.map(({x,y})=>[x-15,y-20,x+19,y+16]);
    occupied.push([width-56,0,width,146],[0,0,37,46]);
    for(const region of regions)titleMark(region.name,artwork[region.name].label,14,occupied);
    titleMark('大塔',[135.735,34.189],12,occupied);
    groups.forEach(pin);
    legend.append(svg('path',{d:'M22 18l-4 15 4-3 4 3Z',fill:'#365446'}),svg('text',{x:22,y:44,fill:'#365446','text-anchor':'middle','font-size':10},'北'));
    const km=[.1,.2,.5,1,2,5,10,20].filter(n=>scale*n/111.195<65).at(-1)||.1;
    const baseline=height-13, length=scale*km/111.195;
    legend.append(svg('path',{d:`M15 ${baseline-4}v4h${length}v-4`,stroke:'#365446',fill:'none','stroke-width':1.4}),svg('text',{x:15,y:baseline-7,'font-size':10,fill:'#365446'},km<1?Math.round(km*1000)+' m':km+' km'));
    plus.disabled=zoom>=16;minus.disabled=zoom<=1;
  }
  function changeZoom(factor,anchor=[width/2,height/2]){
    const next=Math.max(1,Math.min(16,zoom*factor));if(next===zoom)return;
    const ratio=1-zoom/next;
    center[0]+=(anchor[0]-width/2)*ratio/scale;center[1]+=(anchor[1]-height/2)*ratio/scale;
    zoom=next;hideChoices();draw();
  }
  const plus=button('＋',()=>changeZoom(2)),minus=button('−',()=>changeZoom(.5)),reset=button('全域',()=>{zoom=1;center=[...home];hideChoices();draw();});
  plus.setAttribute('aria-label','地図を拡大');minus.setAttribute('aria-label','地図を縮小');toolbar.append(plus,minus,reset);
  let drag;
  canvas.onpointerdown=e=>{
    if(e.button!==0||e.target.closest('.rm-pin')||drag)return;
    canvas.setPointerCapture(e.pointerId);drag={id:e.pointerId,x:e.clientX,y:e.clientY};hideChoices();
  };
  canvas.onpointermove=e=>{
    if(!drag||e.pointerId!==drag.id)return;
    center[0]+=(drag.x-e.clientX)/scale;center[1]+=(drag.y-e.clientY)/scale;
    drag.x=e.clientX;drag.y=e.clientY;draw();
  };
  canvas.onpointerup=canvas.onpointercancel=e=>{if(e.pointerId===drag?.id)drag=null;};
  canvas.onkeydown=e=>{
    if(e.key==='+'||e.key==='='){e.preventDefault();changeZoom(2);return;}
    if(e.key==='-'){e.preventDefault();changeZoom(.5);return;}
    const delta={ArrowRight:[1,0],ArrowLeft:[-1,0],ArrowUp:[0,-1],ArrowDown:[0,1]}[e.key];
    if(delta){e.preventDefault();center=center.map((v,i)=>v+delta[i]*48/scale);hideChoices();draw();}
  };
  draw();
  const observer=new ResizeObserver(draw);observer.observe(stage);
  mounted.set(container,()=>observer.disconnect());
}
