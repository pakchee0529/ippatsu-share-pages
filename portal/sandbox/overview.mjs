export function overview(panel) {
  const box=document.createElement('section'), heading=document.createElement('h2');
  heading.textContent='全体地図';
  const canvas=document.createElement('div'),note=document.createElement('p');
  canvas.className='survey-map';canvas.setAttribute('aria-label','訪問順と径間の位置');
  note.textContent='座標を照合すると径間の位置を表示します。';
  box.append(heading,note,canvas);panel.prepend(box);
  let map,markers;
  return rows=>{
    const points=rows.filter(r=>r.center);
    if(!points.length)return;
    if(!window.L){note.textContent='地図を読み込めません。各径間の2点地図を利用できます。';return;}
    const first=!map;
    if(first){
      canvas.hidden=false;
      map=L.map(canvas,{scrollWheelZoom:false});
      L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png',{maxZoom:19,attribution:'&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'}).addTo(map);
      markers=L.layerGroup().addTo(map);
    }
    markers.clearLayers();
    rows.forEach((r,i)=>{
      if(!r.center)return;
      const link=document.createElement('a');link.href=r.url;link.target='_blank';link.rel='noopener noreferrer';link.textContent=(i+1)+'　'+r.name+' の2点地図';
      L.marker(r.center,{title:r.name,icon:L.divIcon({className:'survey-pin',html:String(i+1),iconSize:[28,28],iconAnchor:[14,14]})}).addTo(markers).bindPopup(link);
    });
    if(first)map.fitBounds(points.map(r=>r.center),{padding:[22,22],maxZoom:17});
    note.textContent=points.length+'径間。番号は訪問リストと同じ順番です。';
  };
}

