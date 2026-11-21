import {deviceCredential} from '../sandbox/device.mjs';

export async function offerClaim(profile,endpoint,manual=false){
 const device=await deviceCredential(false).catch(()=>null);
 if(!device){if(manual)alert('このブラウザには引き継ぎ元の端末情報がありません。');return}
 async function request(action,fields={}){
  const response=await fetch(endpoint,{method:'POST',headers:{'Content-Type':'application/json','x-ippatsu-session':profile.token},body:JSON.stringify({action,device,...fields})});
  const data=await response.json();
  if(!response.ok)throw Object.assign(Error(data.message||'ログインし直してください。'),{status:response.status});
  return data;
 }
 let items;
 try{({items}=await request('claimPreview'))}catch{alert('引き継ぎ一覧を取得できませんでした。砂場の「端末から引き継ぐ」で再確認できます。');return}
 if(!items.length){if(manual)alert('引き継げるページや写真はありません。');return}
 const dlg=document.createElement('dialog');dlg.className='account-sheet claim-sheet';
 dlg.innerHTML='<h2>この端末から引き継ぐ</h2><p class="destination"></p><p>自分で作ったものだけ選んでください。共用端末では他の人の作品が含まれることがあります。</p><div class="choices"></div><p role="status"></p><button class="apply" disabled>選んだものを引き継ぐ</button> <button class="skip">あとで</button>';
 dlg.querySelector('.destination').textContent='引き継ぎ先：'+profile.name;
 const choices=dlg.querySelector('.choices'),status=dlg.querySelector('[role=status]'),apply=dlg.querySelector('.apply'),skip=dlg.querySelector('.skip');
 for(const item of items){
  const label=document.createElement('label'),check=document.createElement('input');check.type='checkbox';
  label.append(check,document.createTextNode(' '+(item.kind==='page'?'ページ':'写真')+'　'+item.title));choices.append(label);
 }
 let busy=false,attempt=null,applied=false;
 const inputs=[...choices.querySelectorAll('input')];
 choices.onchange=()=>{const n=inputs.filter(i=>i.checked).length;apply.disabled=!n;apply.textContent=n?n+'件を引き継ぐ':'選んだものを引き継ぐ'};
 const finished=new Promise(resolve=>dlg.onclose=()=>{dlg.remove();resolve()});
 skip.onclick=()=>dlg.close();dlg.oncancel=e=>{if(busy)e.preventDefault()};
 apply.onclick=async()=>{
  if(busy)return;
  attempt??={requestId:crypto.randomUUID(),items:items.filter((_,i)=>inputs[i].checked).map(({kind,id,version})=>({kind,id,version}))};
  busy=true;apply.disabled=skip.disabled=true;inputs.forEach(i=>i.disabled=true);
  try{const result=await request('claimApply',attempt);applied=true;status.textContent=result.count+'件を引き継ぎました。';apply.hidden=true;skip.textContent='続ける'}
  catch(err){status.textContent=err.message;apply.disabled=false;
   if(err.status===409){apply.hidden=true;skip.textContent='閉じる'}else{apply.textContent='同じ内容でもう一度確認'}
  }finally{busy=false;skip.disabled=false}
 };
 document.body.append(dlg);dlg.showModal();await finished;return applied;
}

