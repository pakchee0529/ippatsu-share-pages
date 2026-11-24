import {previewPage} from '../sandbox/preview.mjs?v=dynamicart1';

export function checkLabel(steps){
  const operated=steps.some(s=>['click','fill'].includes(s.action));
  const result=steps.some((s,i)=>s.action.startsWith('expect') && steps.slice(0,i).some(a=>a.action==='click'||(a.action==='fill'&&a.id!==s.id)));
  const inputOnly=steps.some((s,i)=>s.action==='expectValue'&&steps.slice(0,i).some(a=>a.action==='fill'&&a.id===s.id));
  return result?'指定した操作と結果を確認済み':inputOnly?'入力値を確認済み':operated?'操作のみ確認済み':steps.length?'初期表示を確認済み':'起動確認のみ';
}

export async function checkStartup(html,steps=[],requireOutcome=false,photo=null,generatedArt=null){
  const values=Object.create(null);
  const shared={values,initial:new Set(),save(key,value){values[key]=value;}};
  const failure=await runPreview(html,steps,shared,requireOutcome,photo,generatedArt);
  if(failure)return failure;
  // Reopen persisted inputs that were already visible at startup, plus explicit value assertions.
  const saved=new Map();
  for(const s of steps){
    if(Object.hasOwn(values,s.id)&&(s.action==='expectValue'||shared.initial.has(s.id)))saved.set(s.id,{action:'expectValue',id:s.id,value:String(values[s.id])});
  }
  if(!saved.size)return '';
  const reopened=await runPreview(html,[...saved.values()],shared,false,photo,generatedArt);
  return reopened?'開き直したとき：'+reopened:'';
}

function runPreview(html,steps,shared,requireOutcome=false,photo=null,generatedArt=null){
  return new Promise(resolve=>{
    const plan=JSON.stringify(steps.slice(0,8)).replaceAll("<","\\u003c");
    const probe = `<script>
      let problem='',initial=[];
      addEventListener('error', e=>{problem=e.message||'Script error'});
      addEventListener('unhandledrejection', e=>{problem=String(e.reason)});
      addEventListener('load',()=>setTimeout(async()=>{
        try{
        const steps=${plan};
        const checkWidth=async()=>{
          const photos=[...document.querySelectorAll('img[data-sandbox-photo="attached"]')];
          if(photos.length){
            await Promise.resolve();
            try{await Promise.all(photos.map(img=>img.decode()));}
            catch{throw Error('掲載写真を読み込めません。写真の指定を確認してください。');}
          }
          const root=document.documentElement, width=root.clientWidth;
          if(root.scrollWidth>width+4)throw Error('スマホ幅'+width+'pxでページが横にはみ出します（'+root.scrollWidth+'px）。表や画像の横幅を調整してください。');
        };
        const fieldValue=el=>['radio','checkbox'].includes(el.type)?String(el.checked):el.value;
        const visible=el=>el?.checkVisibility({opacityProperty:true,visibilityProperty:true}) && el.getClientRects().length;
        if(${requireOutcome?'true':'false'} && [...document.querySelectorAll('button,input[type=button],input[type=submit]')].some(el=>visible(el)&&!el.disabled)
          && !steps.some((s,i)=>s.action.startsWith('expect')&&steps.slice(0,i).some(a=>a.action==='click'||(a.action==='fill'&&a.id!==s.id)))){
          throw Error('操作ボタンのあるページです。主要操作と、その結果を確かめる検査手順を返してください。');
        }
        initial=steps.filter(s=>visible(document.getElementById(s.id))).map(s=>s.id);
        await checkWidth();
        let beforeActions=null;
        for(const s of steps){
          if(${requireOutcome?'true':'false'}&&!beforeActions&&['fill','click'].includes(s.action)){
            beforeActions=new Map(steps.filter(x=>x.action.startsWith('expect')).map(x=>{
              const target=document.getElementById(x.id);
              return [x.action+':'+x.id,visible(target)?(x.action==='expectText'?target.innerText:fieldValue(target)):null];
            }));
          }
          const deadline=performance.now()+1100;
          let reason='検査対象がありません: '+s.id;
          while(true){
            const el=document.getElementById(s.id);
            if(el&&document.querySelectorAll('#'+CSS.escape(s.id)).length>1)throw Error('検査対象のIDが重複しています: '+s.id);
            if(visible(el)){
              if(s.action==='expectText' || s.action==='expectValue'){
                const matches=s.action==='expectText'?Boolean(s.value)&&el.innerText?.includes(s.value):fieldValue(el)===s.value;
                if(matches){
                  const value=s.action==='expectText'?el.innerText:fieldValue(el);
                  if(beforeActions?.get(s.action+':'+s.id)!==value){beforeActions=null;break;}
                  reason=s.id+' の結果は操作前から同じです。結果が変わる条件で検査してください';
                }else reason=s.id+' の結果が期待値 '+s.value+' に変わりませんでした';
              }else{
                el.scrollIntoView({block:'center',inline:'center',behavior:'instant'});
                const r=el.getBoundingClientRect();
                const hit=document.elementFromPoint((Math.max(0,r.left)+Math.min(innerWidth,r.right))/2,(Math.max(0,r.top)+Math.min(innerHeight,r.bottom))/2);
                reason=s.id+' を画面から操作できません';
                if(hit && el.contains(hit) && !el.matches(':disabled,[aria-disabled="true"]') && !el.closest('[inert]')){
                  if(s.action==='click'){el.click();break;}
                  if(s.action==='fill' && el.matches('textarea,select,input:not([type=hidden]):not([type=file]):not([type=button]):not([type=submit]):not([type=reset])') && !el.readOnly){if(['checkbox','radio'].includes(el.type)){if(!['true','false'].includes(s.value))throw Error(s.id+' のチェック値を確認してください');el.checked=s.value==='true';}else el.value=s.value;if(fieldValue(el)!==s.value)throw Error(s.id+' に指定の値を入力できません');el.dispatchEvent(new Event('input',{bubbles:true}));el.dispatchEvent(new Event('change',{bubbles:true}));break;}
                }
              }
            }else reason=s.id+' が画面に表示されていません';
            if(performance.now()>=deadline)throw Error(reason);
            await new Promise(resolve=>setTimeout(resolve,50));
          }
        }
        await checkWidth();
        }catch(e){problem=e.message;}
        setTimeout(()=>parent.postMessage({sandboxStartup:problem.slice(0,220),initial},'*'),200);
      },100));
    </script>`;
    const controller=new AbortController();
    const frame=previewPage(probe+html,"isolated-test",{...shared,signal:controller.signal},photo,generatedArt);
    frame.style.cssText='position:fixed;left:-2000px;top:0;width:360px;height:750px;opacity:0;pointer-events:none';
    frame.setAttribute('aria-hidden','true');
    frame.tabIndex=-1;
    function finish(result){
      controller.abort();
      clearTimeout(timeout);
      window.removeEventListener('message',receive);
      frame.remove();
      resolve(result);
    }
    function receive(event){
      if(event.source===frame.contentWindow && event.origin==='null' && typeof event.data?.sandboxStartup==='string'){
        for(const id of event.data.initial||[])shared.initial.add(id);
        finish(event.data.sandboxStartup);
      }
    }
    const timeout=setTimeout(()=>finish('起動の応答がありません'),12000);
    window.addEventListener('message',receive);
    document.body.append(frame);
  });
}
