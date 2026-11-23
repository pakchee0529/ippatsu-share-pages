import {previewPage} from '../sandbox/preview.mjs';

export function checkStartup(html,steps=[]){
  return new Promise(resolve=>{
    const plan=JSON.stringify(steps.slice(0,8)).replaceAll("<","\\u003c");
    const probe = `<script>
      let problem='';
      addEventListener('error', e=>{problem=e.message||'Script error'});
      addEventListener('unhandledrejection', e=>{problem=String(e.reason)});
      addEventListener('load',()=>setTimeout(async()=>{
        try{
        const steps=${plan};
        for(const s of steps){
          const el=document.getElementById(s.id);
          if(!el)throw Error('検査対象がありません: '+s.id);
          if(s.action==='click'){if(el.disabled)throw Error('操作できません: '+s.id);el.click();}
          if(s.action==='fill'){el.value=s.value;el.dispatchEvent(new Event('input',{bubbles:true}));el.dispatchEvent(new Event('change',{bubbles:true}));}
          if(s.action==='expectText' && (!s.value||!el.textContent.includes(s.value)))throw Error(s.id+' の表示が期待値 '+s.value+' と違います');
          if(s.action==='expectValue' && el.value!==s.value)throw Error(s.id+' の値が期待値 '+s.value+' と違います');
          await new Promise(r=>setTimeout(r,75));
        }
        const button=[...document.querySelectorAll('button')].find(b=>!b.disabled && b.getClientRects().length && /^(はじめる|始める|スタート|ゲーム開始|練習する|計算する)$/.test(b.textContent.trim()));
        if(!steps.length && button)button.click();
        }catch(e){problem=e.message;}
        setTimeout(()=>parent.postMessage({sandboxStartup:problem.slice(0,220)},'*'),200);
      },100));
    </script>`;
    const frame=previewPage(probe+html);
    frame.style.cssText='position:fixed;left:-2000px;top:0;width:390px;height:750px;visibility:hidden';
    frame.setAttribute('aria-hidden','true');
    frame.tabIndex=-1;
    function finish(result){
      clearTimeout(timeout);
      window.removeEventListener('message',receive);
      frame.remove();
      resolve(result);
    }
    function receive(event){
      if(event.source===frame.contentWindow && event.origin==='null' && typeof event.data?.sandboxStartup==='string')finish(event.data.sandboxStartup);
    }
    const timeout=setTimeout(()=>finish('起動の応答がありません'),5000);
    window.addEventListener('message',receive);
    document.body.append(frame);
  });
}
