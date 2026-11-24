import {bundledArt} from './bundled-art.mjs';
import {displayArt} from './generated-art.mjs';
import {displayPhoto} from './attached-photo.mjs';
export function previewPage(html, inputKey=null, shared=null, photo=null, generatedArt=null) {
  const frame = document.createElement("iframe");
  frame.title = "砂場のページ";
  frame.setAttribute("sandbox", "allow-scripts");
  frame.referrerPolicy = "no-referrer";
  const policy = "default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; img-src data: blob:; font-src data:; form-action 'none'; base-uri 'none'; frame-src 'none'; connect-src 'none'";
  const localForms = `<script>
    document.addEventListener("click", event => {
      const button = event.target.closest?.("button,input");
      if (event.defaultPrevented || !button?.form || !["submit","image"].includes(button.type)) return;
      event.preventDefault();
      const form = button.form;
      if (form.noValidate || button.formNoValidate || form.reportValidity())
        form.dispatchEvent(new SubmitEvent("submit",{bubbles:true,cancelable:true,submitter:button}));
    });
  </script>`;
  let bridge = "";
  if(inputKey){
    let state=shared?.values||{};
    try{if(!shared)state=JSON.parse(localStorage.getItem(inputKey)||"{}");}catch{}
    const initial=JSON.stringify(state).replaceAll("<","\\u003c");
    bridge='<script>const saved='+initial+';function key(e){return e.id||e.name}function supported(e){return e.matches("textarea,select,input")&&!["password","file","hidden","submit","button","reset"].includes(e.type)&&key(e)}document.addEventListener("DOMContentLoaded",()=>{for(const e of document.querySelectorAll("input,textarea,select")){if(supported(e)&&Object.hasOwn(saved,key(e))){if(["checkbox","radio"].includes(e.type))e.checked=saved[key(e)]===true;else e.value=saved[key(e)]}}});document.addEventListener("input",({target:e})=>{if(supported(e))parent.postMessage({field:key(e),value:["checkbox","radio"].includes(e.type)?e.checked:e.value},"*")});<\/script>';
    window.addEventListener("message",event=>{
      if(event.source!==frame.contentWindow || event.origin!=="null")return;
      const d=event.data;
      if(!d||typeof d.field!=="string"||d.field.length>120||!["string","boolean"].includes(typeof d.value)||String(d.value).length>8000)return;
      state={...state,[d.field]:d.value};
      if(shared){shared.save(d.field,d.value);return;}
      try{localStorage.setItem(inputKey,JSON.stringify(state));}catch{}
    },shared?.signal?{signal:shared.signal}:undefined);
  }
  const head = '<!doctype html><meta charset="utf-8"><meta http-equiv="Content-Security-Policy" content="' + policy + '">' + localForms + bridge;
  const body=displayArt(displayPhoto(html,photo),generatedArt);
  const art=bundledArt(html);
  if(art)art.then(binding=>{frame.srcdoc=head+binding+body;});
  else frame.srcdoc=head+body;
  return frame;
}
