const maxBytes = 500000;
const maxEdge = 1600;
const maxArrows = 24;
const svgNS = 'http://www.w3.org/2000/svg';

function arrowPath(arrow, width, height) {
  const x1 = arrow.x1 * width, y1 = arrow.y1 * height;
  const x2 = arrow.x2 * width, y2 = arrow.y2 * height;
  const angle = Math.atan2(y2 - y1, x2 - x1);
  const head = Math.min(Math.hypot(x2 - x1, y2 - y1) * .48, Math.min(width, height) * .05);
  return `M ${x1} ${y1} L ${x2} ${y2} M ${x2-head*Math.cos(angle-.55)} ${y2-head*Math.sin(angle-.55)} L ${x2} ${y2} L ${x2-head*Math.cos(angle+.55)} ${y2-head*Math.sin(angle+.55)}`;
}

function paintArrows(arrows, width, height, stroke) {
  const tokens = getComputedStyle(document.documentElement);
  const line = Math.max(2, Math.min(width, height) * .010);
  for (const arrow of arrows) {
    const path = arrowPath(arrow, width, height);
    stroke(path, line * 1.7, tokens.getPropertyValue('--white').trim());
    stroke(path, line, tokens.getPropertyValue('--arrow').trim());
  }
}

export function addOverlay(container, image, arrows) {
  if (!arrows.length) return;
  const svg = document.createElementNS(svgNS, 'svg');
  svg.setAttribute('aria-hidden', 'true');
  container.append(svg);
  const update = () => {
    const width = image.naturalWidth, height = image.naturalHeight;
    if (!width || !height) return;
    svg.setAttribute('viewBox', `0 0 ${width} ${height}`);
    svg.replaceChildren();
    paintArrows(arrows, width, height, (d, size, color) => {
      const path = document.createElementNS(svgNS, 'path');
      for (const [key, value] of Object.entries({d, stroke:color, fill:'none','stroke-width':size,'stroke-linecap':'round','stroke-linejoin':'round'})) path.setAttribute(key,value);
      svg.append(path);
    });
  };
  image.addEventListener('load', update);
  if (image.complete) update();
}

export async function compressPhoto(file) {
  const url = URL.createObjectURL(file);
  const image = new Image();
  image.src = url;
  try {
    await image.decode();
    let scale = Math.min(1, maxEdge / Math.max(image.naturalWidth, image.naturalHeight));
    const source = document.createElement('canvas');
    for (let attempt = 0; attempt < 5; attempt++) {
      source.width = Math.max(1, Math.round(image.naturalWidth * scale));
      source.height = Math.max(1, Math.round(image.naturalHeight * scale));
      const ctx = source.getContext('2d');
      ctx.fillStyle = '#fff';
      ctx.fillRect(0,0,source.width,source.height);
      ctx.drawImage(image,0,0,source.width,source.height);
      const blob = await new Promise(resolve=>source.toBlob(resolve,'image/jpeg',.82));
      if (blob && blob.size <= maxBytes) return blob;
      scale *= .75;
    }
    throw Error('写真を縮小できませんでした。');
  } finally { URL.revokeObjectURL(url); }
}

export function photoEditor(canvas, undo, notify) {
  const ctx = canvas.getContext('2d');
  let image, arrows = [], draft, pointer, version = 0;
  function repaint() {
    undo.disabled = !arrows.length;
    if (!image) return;
    ctx.drawImage(image.source,0,0);
    paintArrows(draft ? arrows.concat(draft) : arrows, canvas.width, canvas.height, (d,size,color)=>{
      ctx.lineCap='round'; ctx.lineJoin='round'; ctx.strokeStyle=color; ctx.lineWidth=size;
      ctx.stroke(new Path2D(d));
    });
  }
  function point(event) {
    const rect = canvas.getBoundingClientRect();
    const clamp = n => Math.max(0,Math.min(1,n));
    return {x:clamp((event.clientX-rect.left)/rect.width),y:clamp((event.clientY-rect.top)/rect.height)};
  }
  canvas.onpointerdown = e => {
    if (!image || pointer!==undefined || e.button!==0) return;
    if (arrows.length >= maxArrows) {notify('矢印は24本までです。');return;}
    const {x,y}=point(e);
    pointer=e.pointerId;
    draft={x1:x,y1:y,x2:x,y2:y};
    canvas.setPointerCapture(pointer);
  };
  canvas.onpointermove = e => {
    if (!draft || pointer!==e.pointerId) return;
    const {x,y}=point(e); draft.x2=x; draft.y2=y; repaint();
  };
  canvas.onpointerup = e => {
    if (!draft || pointer!==e.pointerId) return;
    const {x,y}=point(e); draft.x2=x; draft.y2=y;
    if (Math.hypot(draft.x2-draft.x1,draft.y2-draft.y1)>.012) arrows.push(draft);
    draft=pointer=undefined; repaint();
  };
  canvas.onpointercancel=()=>{draft=pointer=undefined; repaint();};
  undo.onclick=()=>{arrows.pop(); repaint();};
  return {
    clear() {version++; image=null; arrows=[]; draft=pointer=undefined; repaint();},
    async show(item) {
      const token=++version;
      const source = new Image(); source.src = item.url;
      await source.decode();
      if (token!==version) return false;
      image={source}; arrows=item.arrows; draft=pointer=undefined;
      canvas.width=source.naturalWidth; canvas.height=source.naturalHeight; repaint();
      return true;
    }
  };
}
