// The app shell is unchanged: keep its cache generation and exact URL keys.
const CACHE='ippatsu-ledger-v2-20261005-2';
const ASSETS=['./','./index.html','./app.js','./app.js?v=20261005-1','./model.js','./style.css'];
const ASSET_URLS=new Set(ASSETS.map(path=>new URL(path,location.href).href));
const NETWORK_TIMEOUT_MS=2000;

self.addEventListener('install',e=>{
  e.waitUntil(caches.open(CACHE).then(c=>c.addAll(ASSETS)).then(()=>self.skipWaiting()));
});
self.addEventListener('activate',e=>{
  e.waitUntil(caches.keys().then(keys=>Promise.all(keys.filter(k=>k.startsWith('ippatsu-ledger-v2-')&&k!==CACHE).map(k=>caches.delete(k)))).then(()=>self.clients.claim()));
});
self.addEventListener('fetch',e=>{
  const u=new URL(e.request.url);
  if(u.origin!==location.origin||e.request.method!=='GET'||!u.pathname.startsWith(new URL('./',location.href).pathname)||e.request.headers.has('range'))return;
  const req=e.request.mode==='navigate'?new Request(new URL('./index.html',location.href)):e.request;
  // Only the existing static app shell may be cached, never API or case data.
  if(!ASSET_URLS.has(req.url))return;
  const cache=caches.open(CACHE).catch(()=>null);
  const cached=cache.then(c=>c?c.match(req):null).then(r=>r&&r.ok?r:null).catch(()=>null);
  const network=fetch(req).then(async r=>{
    // A 200 header is not enough: a stalled body must also lose to the cache.
    // Only buffer these small, known shell assets when a healthy fallback exists.
    if(r.ok&&await cached)await r.clone().arrayBuffer();
    return r;
  });
  // Keep a late successful fetch alive to refresh this generation's exact key.
  // Cache failures must not turn a successful network response into an error.
  e.waitUntil(network.then(r=>{
    if(!r.ok)return;
    const copy=r.clone();
    return cache.then(c=>c?c.put(req,copy):undefined);
  }).catch(()=>{}));
  e.respondWith(cached.then(async hit=>{
    // First visits and cache misses still need the real network result.
    if(!hit)return network;
    let timer;
    try{
      return await Promise.race([
        network.then(r=>r.ok?r:hit,()=>hit),
        new Promise(resolve=>{timer=setTimeout(()=>resolve(hit),NETWORK_TIMEOUT_MS);})
      ]);
    }finally{clearTimeout(timer);}
  }));
});
