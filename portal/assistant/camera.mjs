export function attachCamera(button,onPhoto,notify){
  let active=null;
  button.addEventListener('click',async()=>{
    if(active)return;
    if(!navigator.mediaDevices?.getUserMedia){notify('このブラウザでカメラを開けません。「ファイル」から写真を選べます。');return;}
    const dialog=document.createElement('dialog'), video=document.createElement('video');
    const take=document.createElement('button'), cancel=document.createElement('button');
    const heading=document.createElement('strong');heading.textContent='紙全体が入るように撮影';
    video.autoplay=true;video.muted=true;video.playsInline=true;
    video.style.cssText='display:block;width:100%;max-height:65dvh;object-fit:contain;background:#172522;margin:.5rem 0';
    take.type=cancel.type='button';take.textContent='この写真を使う';cancel.textContent='キャンセル';take.disabled=true;
    dialog.setAttribute('aria-label','現調資料を撮影');dialog.style.cssText='width:min(90vw,38rem);box-sizing:border-box';
    dialog.append(heading,video,take,cancel);document.body.append(dialog);
    let stream,closed=false;
    function stop(){stream?.getTracks().forEach(track=>track.stop());video.srcObject=null;}
    function close(){if(closed)return;closed=true;stop();dialog.remove();window.removeEventListener('pagehide',close);document.removeEventListener('visibilitychange',hidden);active=null;button.focus();}
    function hidden(){if(document.hidden)close();}
    active=dialog;cancel.onclick=close;dialog.oncancel=close;window.addEventListener('pagehide',close);document.addEventListener('visibilitychange',hidden);
    dialog.showModal();
    video.onplaying=()=>{take.disabled=false;};
    take.onclick=async()=>{
      if(!video.videoWidth||take.disabled)return;
      take.disabled=true;
      const canvas=document.createElement('canvas');
      try{
        const scale=Math.min(1,1500/Math.max(video.videoWidth,video.videoHeight));
        canvas.width=Math.max(1,Math.round(video.videoWidth*scale));canvas.height=Math.max(1,Math.round(video.videoHeight*scale));
        canvas.getContext('2d').drawImage(video,0,0,canvas.width,canvas.height);
        stop();
        const blob=await new Promise(resolve=>canvas.toBlob(resolve,'image/jpeg',0.9));
        if(!blob)throw Error();
        if(!closed)onPhoto(new File([blob],'現調資料.jpg',{type:'image/jpeg'}));
      }catch{notify('撮影した写真を取り込めませんでした。もう一度撮影できます。');}
      finally{canvas.width=canvas.height=1;close();}
    };
    try{
      stream=await navigator.mediaDevices.getUserMedia({audio:false,video:{facingMode:{ideal:'environment'},width:{ideal:1600,max:1920},height:{ideal:1200,max:1920}}});
      if(closed){stop();return;}
      video.srcObject=stream;await video.play();
    }catch(e){if(!closed)notify(e.name==='NotAllowedError'?'カメラの使用を許可するか、「ファイル」から写真を選んでください。':'カメラを開けませんでした。「ファイル」から写真を選べます。');close();}
  });
}
