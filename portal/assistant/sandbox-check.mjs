import {previewPage} from '../sandbox/preview.mjs';

export function checkStartup(html){
  return new Promise(resolve=>{
    const probe = `<script>
      let problem='';
      addEventListener('error', e=>{problem=e.message||'Script error'});
      addEventListener('unhandledrejection', e=>{problem=String(e.reason)});
      addEventListener('load',()=>setTimeout(()=>{
        parent.postMessage({sandboxStartup:problem.slice(0,220)},'*');
      },150));
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
