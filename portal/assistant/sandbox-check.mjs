import {previewPage} from '../sandbox/preview.mjs';

export function checkLabel(steps){
  const operated=steps.some(s=>['click','fill'].includes(s.action));
  const result=steps.some((s,i)=>s.action.startsWith('expect') && steps.slice(0,i).some(a=>['click','fill'].includes(a.action)));
  return result?'指定した操作と結果を確認済み':operated?'操作のみ確認済み':steps.length?'初期表示を確認済み':'起動確認のみ';
}

export async function checkStartup(html,steps=[]){
  const values=Object.create(null);
  const shared={values,save(key,value){values[key]=value;}};
  const failure=await runPreview(html,steps,shared);
  if(failure)return failure;
  // Reopen only values covered by explicit assertions and written via the real input bridge.
  const saved=new Map();
  for(const s of steps){
    if(s.action==='expectValue' && Object.hasOwn(values,s.id))saved.set(s.id,s);
  }
  if(!saved.size)return '';
  const reopened=await runPreview(html,[...saved.values()],shared);
  return reopened?'開き直したとき：'+reopened:'';
}

function runPreview(html,steps,shared){
  return new Promise(resolve=>{
    const plan=JSON.stringify(steps.slice(0,8)).replaceAll("<","\\u003c");
    const probe = `<script>
      let problem='';
      addEventListener('error', e=>{problem=e.message||'Script error'});
      addEventListener('unhandledrejection', e=>{problem=String(e.reason)});
      addEventListener('load',()=>setTimeout(async()=>{
        try{
        const steps=${plan};
        const visible=el=>el?.checkVisibility({opacityProperty:true,visibilityProperty:true}) && el.getClientRects().length;
        for(const s of steps){
          const deadline=performance.now()+1100;
          let reason='検査対象がありません: '+s.id;
          while(true){
            const el=document.getElementById(s.id);
            if(visible(el)){
              if(s.action==='expectText' || s.action==='expectValue'){
                const matches=s.action==='expectText'?Boolean(s.value)&&el.innerText?.includes(s.value):el.value===s.value;
                if(matches)break;
                reason=s.id+' の結果が期待値 '+s.value+' に変わりませんでした';
              }else{
                el.scrollIntoView({block:'center',inline:'center',behavior:'instant'});
                const r=el.getBoundingClientRect();
                const hit=document.elementFromPoint((Math.max(0,r.left)+Math.min(innerWidth,r.right))/2,(Math.max(0,r.top)+Math.min(innerHeight,r.bottom))/2);
                reason=s.id+' を画面から操作できません';
                if(hit && el.contains(hit) && !el.matches(':disabled,[aria-disabled="true"]') && !el.closest('[inert]')){
                  if(s.action==='click'){el.click();break;}
                  if(s.action==='fill' && 'value' in el && !el.readOnly){el.value=s.value;el.dispatchEvent(new Event('input',{bubbles:true}));el.dispatchEvent(new Event('change',{bubbles:true}));break;}
                }
              }
            }else reason=s.id+' が画面に表示されていません';
            if(performance.now()>=deadline)throw Error(reason);
            await new Promise(resolve=>setTimeout(resolve,50));
          }
        }
        }catch(e){problem=e.message;}
        setTimeout(()=>parent.postMessage({sandboxStartup:problem.slice(0,220)},'*'),200);
      },100));
    </script>`;
    const controller=new AbortController();
    const frame=previewPage(probe+html,"isolated-test",{...shared,signal:controller.signal});
    frame.style.cssText='position:fixed;left:-2000px;top:0;width:390px;height:750px;opacity:0;pointer-events:none';
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
      if(event.source===frame.contentWindow && event.origin==='null' && typeof event.data?.sandboxStartup==='string')finish(event.data.sandboxStartup);
    }
    const timeout=setTimeout(()=>finish('起動の応答がありません'),12000);
    window.addEventListener('message',receive);
    document.body.append(frame);
  });
}
