const office = {name:'会社（五條市上之町）',point:[34.379692,135.672989],kind:'office'};
function node(tag,text){const el=document.createElement(tag);el.textContent=text;return el;}
function button(label,fn){const el=node('button',label);el.type='button';el.onclick=fn;return el;}
export function currentOrigin(){
  return new Promise((resolve,reject)=>{
    if(!navigator.geolocation){reject(Error('この端末は現在地を取得できません。ほかの起点を選んでください。'));return;}
    navigator.geolocation.getCurrentPosition(({coords})=>{
      resolve({name:'現在地',point:[coords.latitude,coords.longitude],kind:'current'});
    },error=>reject(Error(error.code===1?'位置情報が許可されていません。端末の設定を確認するか、ほかの起点を選んでください。':'現在地を取得できませんでした。もう一度試すか、ほかの起点を選んでください。')),
    {enableHighAccuracy:true,timeout:12000,maximumAge:30000});
  });
}
function coordinates(text){
  const m=text.normalize('NFKC').trim().match(/^([+-]?\d+(?:\.\d+)?)\s*[,、\s]\s*([+-]?\d+(?:\.\d+)?)$/u);
  if(!m)return;
  const p=m.slice(1).map(Number);
  if(Math.abs(p[0])<=90 && Math.abs(p[1])<=180)return p;
}
export function originPicker(rows,lastChecked){
  let selected=office,active=null;
  function choose(){
    if(active)return active;
    const modal=node('dialog','');modal.className='survey-origin';
    modal.style.cssText='box-sizing:border-box;width:min(28rem,95vw);max-height:85dvh;overflow:auto';
    const title=node('h2','出発地点を選ぶ');title.id='survey-origin-title';modal.setAttribute('aria-labelledby',title.id);
    const select=node('select','');select.setAttribute('aria-label','出発地点の種類');select.style.maxWidth='100%';
    const last=lastChecked();
    const options=[['office',office.name],['current','現在地'],...(last?[['last','最後にチェックした径間（'+last.name+'）']]:[]),['row','リストの径間'],['coordinates','緯度・経度'],['map','地図で選ぶ']];
    for(const [value,label] of options)select.add(new Option(label,value));select.value=selected.kind==='last'&&!last?'office':selected.kind;
    const area=node('div',''),status=node('p','');status.setAttribute('role','status');
    const actions=node('div','');actions.className='survey-actions';
    let map,marker,point,field,epoch=0,settle;
    const close=value=>{if(!modal.isConnected)return;epoch++;map?.remove();modal.close();modal.remove();active=null;settle(value);};
    const apply=button('この地点を使う',async()=>{
      const run=++epoch,kind=select.value;let origin;
      try{
        if(kind==='office')origin=office;
        if(kind==='last')origin=last;
        if(kind==='current'){apply.disabled=true;status.textContent='現在地を取得しています…';origin=await currentOrigin();}
        if(kind==='row'){const row=rows.find(r=>r.key===field.value);if(row?.center)origin={point:row.center,name:row.name,kind,key:row.key};}
        if(kind==='coordinates'||kind==='map'){
          const p=kind==='coordinates'?coordinates(field.value):point;
          if(!p)throw Error(kind==='map'?'地図をタップして起点を指定してください。':'緯度と経度をカンマで区切って入力してください。');
          origin={point:p,name:(kind==='map'?'地図の指定地点':'指定座標')+'（'+p.map(n=>n.toFixed(5)).join(', ' )+'）',kind};
        }
        if(run!==epoch)return;
        if(!origin)throw Error('位置を確認できる径間を選んでください。');
        selected=origin;close(origin);
      }catch(e){if(run===epoch)status.textContent=e.message;}finally{if(run===epoch)apply.disabled=false;}
    });
    function fields(){
      epoch++;map?.remove();map=null;marker=null;field=null;point=null;area.replaceChildren();status.textContent='';apply.disabled=false;
      if(select.value==='row'){
        field=node('select','');field.setAttribute('aria-label','起点にする径間');field.style.maxWidth='100%';
        for(const row of rows.filter(r=>r.center))field.add(new Option(row.name,row.key));
        if(selected.kind==='row'&&rows.some(r=>r.key===selected.key&&r.center))field.value=selected.key;
        area.append(field);if(!field.options.length){status.textContent='位置を確認できる径間がありません。ほかの起点を選んでください。';apply.disabled=true;}
      }else if(select.value==='coordinates'){
        field=node('input','');field.setAttribute('aria-label','緯度・経度');field.placeholder='緯度, 経度';if(selected.kind==='coordinates')field.value=selected.point.join(', ');area.append(field);
      }else if(select.value==='map'){
        if(!window.L){status.textContent='地図を読み込めませんでした。緯度・経度でも指定できます。';apply.disabled=true;return;}
        const canvas=node('div','');canvas.style.cssText='height:32dvh;min-height:12rem;margin:.5rem 0';canvas.setAttribute('aria-label','起点を選ぶ地図');area.append(canvas);
        map=window.L.map(canvas).setView(selected.point,13);
        window.L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png',{maxZoom:19,attribution:'© OpenStreetMap contributors'}).addTo(map);
        function mark(p){point=p;marker?.remove();marker=window.L.circleMarker(p,{radius:7}).addTo(map);status.textContent='指定地点 '+p.map(n=>n.toFixed(5)).join(', ');}
        status.textContent='地図をタップして起点を指定してください。';if(selected.kind==='map')mark(selected.point);
        map.on('click',e=>mark([e.latlng.lat,e.latlng.lng]));
      }
    }
    select.onchange=fields;actions.append(apply,button('キャンセル',()=>close(null)));modal.append(title,select,area,status,actions);
    modal.oncancel=e=>{e.preventDefault();close(null);};
    document.body.append(modal);modal.showModal();active=new Promise(resolve=>settle=resolve);fields();return active;
  }
  return {choose,current:()=>selected};
}
