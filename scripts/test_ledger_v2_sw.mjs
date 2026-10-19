// Synthetic service-worker regression tests. No network or production data.
// Run: node scripts/test_ledger_v2_sw.mjs
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {runInNewContext} from 'node:vm';

const source=readFileSync(new URL('../portal/ledger-v2/sw.js',import.meta.url),'utf8');
const BASE='https://example.test/ippatsu-share-pages/portal/ledger-v2/';
const CACHE='ippatsu-ledger-v2-20261005-2';
const ASSETS=['','index.html','app.js','app.js?v=20261005-1','model.js','style.css'];
const flush=()=>new Promise(resolve=>setImmediate(resolve));
function deferred(){let resolve,reject;const promise=new Promise((a,b)=>{resolve=a;reject=b;});return {promise,resolve,reject};}
function harness({seed={},other={},fetchImpl,openError=false,matchError=false,putError=false,installError=false}={}){
  const listeners={},timers=new Map(),stores=new Map([[CACHE,new Map(Object.entries(seed))],...Object.entries(other).map(([k,v])=>[k,new Map(Object.entries(v))])]);
  const calls={fetch:[],put:[],open:[],deleted:[],skip:0,claim:0,add:[]};let nextTimer=0;
  const url=x=>typeof x==='string'?new URL(x,BASE).href:x.url;
  const cacheFor=name=>({
    match:async req=>{if(matchError)throw Error('cache read');return stores.get(name)?.get(url(req))?.clone();},
    put:async(req,response)=>{if(putError)throw Error('quota');calls.put.push(url(req));stores.get(name).set(url(req),response.clone());},
    addAll:async paths=>{calls.add.push(paths);if(installError)throw Error('partial install');const values=paths.map(p=>[url(p),new Response('installed '+p)]);for(const [p,r] of values)stores.get(name).set(p,r);}
  });
  const pending=deferred();
  const sandbox={URL,Request,Response,Set,location:new URL(BASE+'sw.js'),
    self:{addEventListener:(name,fn)=>listeners[name]=fn,skipWaiting:async()=>{calls.skip++;},clients:{claim:async()=>{calls.claim++;}}},
    caches:{open:async name=>{calls.open.push(name);if(openError)throw Error('cache disabled');if(!stores.has(name))stores.set(name,new Map());return cacheFor(name);},keys:async()=>[...stores.keys()],delete:async name=>{calls.deleted.push(name);return stores.delete(name);}},
    fetch:req=>{calls.fetch.push(req);return fetchImpl?fetchImpl(req):pending.promise;},
    setTimeout:(fn,ms)=>{const id=++nextTimer;timers.set(id,{fn,ms});return id;},clearTimeout:id=>timers.delete(id)
  };
  runInNewContext(source,sandbox);
  function dispatch(path='app.js',options={}){
    const req=options.navigate?{url:new URL(path,BASE).href,method:'GET',mode:'navigate',headers:new Headers()}:new Request(new URL(path,BASE),options);
    const waits=[];let response;
    listeners.fetch({request:req,waitUntil:p=>waits.push(p),respondWith:p=>response=p});
    return {response,waits,settle:()=>Promise.all(waits)};
  }
  async function lifecycle(name){const waits=[];listeners[name]({waitUntil:p=>waits.push(p)});await Promise.all(waits);}
  async function tick(){const tasks=[...timers.entries()];for(const [id,{fn,ms}] of tasks){assert.equal(ms,2000);timers.delete(id);fn();}await flush();}
  return {dispatch,lifecycle,tick,pending,calls,timers,stores,body:async(path,name=CACHE)=>stores.get(name)?.get(new URL(path,BASE).href)?.clone().text()};
}
const hit=(body='cached',status=200)=>new Response(body,{status});
const seed=(path='app.js',body='cached',status=200)=>({[BASE+path]:hit(body,status)});
const tests=[];
const test=(name,fn)=>tests.push([name,fn]);

test('normal network wins, refreshes the exact key, and clears timer',async()=>{
 const h=harness({seed:seed()});const e=h.dispatch();await flush();h.pending.resolve(hit('fresh'));assert.equal(await (await e.response).text(),'fresh');await e.settle();assert.equal(await h.body('app.js'),'fresh');assert.equal(h.timers.size,0);assert.deepEqual(h.calls.put,[BASE+'app.js']);
});
test('hung network returns healthy cache at 2000 ms; late success stays in waitUntil',async()=>{
 const h=harness({seed:seed()});const e=h.dispatch();let done=false,backgroundDone=false;e.response.then(()=>done=true);e.settle().then(()=>backgroundDone=true);await flush();assert.equal(done,false);assert.equal(e.waits.length,1);await h.tick();assert.equal(await (await e.response).text(),'cached');assert.equal(backgroundDone,false);h.pending.resolve(hit('late'));await e.settle();assert.equal(await h.body('app.js'),'late');assert.equal(h.timers.size,0);
});
test('200 headers with a stalled body still fall back; late complete body refreshes cache',async()=>{
 let stream;const body=new ReadableStream({start(c){stream=c;c.enqueue(new TextEncoder().encode('first '));}});
 const h=harness({seed:seed(),fetchImpl:()=>Promise.resolve(new Response(body))});const e=h.dispatch();let done=false;e.response.then(()=>done=true);await flush();assert.equal(done,false);assert.equal(h.calls.put.length,0);await h.tick();assert.equal(await (await e.response).text(),'cached');stream.enqueue(new TextEncoder().encode('last'));stream.close();await e.settle();assert.equal(await h.body('app.js'),'first last');assert.equal(h.timers.size,0);
});
test('200 headers followed by a broken body return healthy cache without pollution',async()=>{
 let stream;const body=new ReadableStream({start(c){stream=c;}});
 const h=harness({seed:seed(),fetchImpl:()=>Promise.resolve(new Response(body))});const e=h.dispatch();await flush();stream.error(Error('broken body'));assert.equal(await (await e.response).text(),'cached');await e.settle();assert.equal(h.calls.put.length,0);assert.equal(h.timers.size,0);
});
test('a late broken body is handled after cache timeout',async()=>{
 let stream;const body=new ReadableStream({start(c){stream=c;}});
 const h=harness({seed:seed(),fetchImpl:()=>Promise.resolve(new Response(body))});const e=h.dispatch();await flush();await h.tick();assert.equal(await (await e.response).text(),'cached');stream.error(Error('late broken body'));await e.settle();assert.equal(await h.body('app.js'),'cached');assert.equal(h.calls.put.length,0);
});
test('no cache does not buffer or pretend to succeed for a stalled body',async()=>{
 let stream;const body=new ReadableStream({start(c){stream=c;}});
 const h=harness({fetchImpl:()=>Promise.resolve(new Response(body))});const e=h.dispatch();const response=await e.response;assert.equal(response.status,200);assert.equal(h.timers.size,0);let complete=false;const read=response.text().then(v=>{complete=true;return v;});await flush();assert.equal(complete,false);stream.enqueue(new TextEncoder().encode('actual body'));stream.close();assert.equal(await read,'actual body');await e.settle();
});
test('late rejection is handled after timeout',async()=>{
 const h=harness({seed:seed()});const e=h.dispatch();await flush();await h.tick();assert.equal(await (await e.response).text(),'cached');h.pending.reject(Error('offline'));await e.settle();assert.equal(await h.body('app.js'),'cached');
});
test('immediate offline rejection returns healthy current-generation cache',async()=>{
 const h=harness({seed:seed(),fetchImpl:()=>Promise.reject(Error('offline'))});const e=h.dispatch();assert.equal(await (await e.response).text(),'cached');await e.settle();assert.equal(h.timers.size,0);
});
for(const status of [404,500,503])test(`HTTP ${status} uses healthy cache without overwriting it`,async()=>{
 const h=harness({seed:seed(),fetchImpl:()=>Promise.resolve(hit('error',status))});const e=h.dispatch();assert.equal(await (await e.response).text(),'cached');await e.settle();assert.equal(await h.body('app.js'),'cached');assert.equal(h.calls.put.length,0);assert.equal(h.timers.size,0);
});
test('no cache keeps waiting for the actual late network response',async()=>{
 const h=harness();const e=h.dispatch();let done=false;e.response.then(()=>done=true);await flush();assert.equal(h.timers.size,0);await h.tick();assert.equal(done,false);h.pending.resolve(hit('first visit'));assert.equal(await (await e.response).text(),'first visit');await e.settle();
});
test('no cache plus rejection stays a real error, never empty success',async()=>{
 const h=harness({fetchImpl:()=>Promise.reject(Error('offline'))});const e=h.dispatch();await assert.rejects(e.response,/offline/);await e.settle();assert.equal(h.timers.size,0);
});
for(const status of [404,500])test(`no cache preserves HTTP ${status}`,async()=>{
 const h=harness({fetchImpl:()=>Promise.resolve(hit('error',status))});const e=h.dispatch();assert.equal((await e.response).status,status);await e.settle();assert.equal(h.calls.put.length,0);
});
test('error cache is not a valid fallback',async()=>{
 const h=harness({seed:seed('app.js','bad cached response',500)});const e=h.dispatch();await flush();assert.equal(h.timers.size,0);h.pending.reject(Error('offline'));await assert.rejects(e.response,/offline/);await e.settle();
});
test('other cache generations cannot supply fallback',async()=>{
 const h=harness({other:{'ippatsu-ledger-v2-old':seed('app.js','old'),unrelated:seed('app.js','unrelated')}});const e=h.dispatch();await flush();assert.equal(h.timers.size,0);h.pending.reject(Error('offline'));await assert.rejects(e.response,/offline/);await e.settle();
});
test('versioned and unversioned app keys stay separate',async()=>{
 const h=harness({seed:{...seed('app.js','bare'),...seed('app.js?v=20261005-1','versioned')},fetchImpl:()=>Promise.reject(Error('offline'))});for(const [path,value] of [['app.js','bare'],['app.js?v=20261005-1','versioned']]){const e=h.dispatch(path);assert.equal(await (await e.response).text(),value);await e.settle();}
});
test('cache for unversioned app cannot mask missing versioned app',async()=>{
 const h=harness({seed:seed('app.js','bare'),fetchImpl:()=>Promise.reject(Error('offline'))});const e=h.dispatch('app.js?v=20261005-1');await assert.rejects(e.response,/offline/);await e.settle();
});
test('navigation keeps URL arguments out of cache keys and uses index.html',async()=>{
 const h=harness({seed:seed('index.html','shell'),fetchImpl:()=>Promise.reject(Error('offline'))});const e=h.dispatch('?date=261020&management_no=00000000',{navigate:true});assert.equal(await (await e.response).text(),'shell');assert.equal(h.calls.fetch[0].url,BASE+'index.html');await e.settle();
});
for(const path of ASSETS)test(`existing static asset ${path||'./'} uses exact cached key`,async()=>{
 const h=harness({seed:seed(path),fetchImpl:()=>Promise.reject(Error('offline'))});const e=h.dispatch(path);assert.equal(await (await e.response).text(),'cached');await e.settle();
});
for(const [name,path,options] of [
 ['other origin','https://api.example.test/model.js',{}],
 ['Supabase API','https://example.supabase.co/functions/v1/photo-ledger-v2?id=fixture',{}],
 ['out of scope','../ledger-input/app.js',{}],
 ['similar prefix','../ledger-v2-other/app.js',{}],
 ['POST','app.js',{method:'POST',body:'fixture'}],
 ['range request','app.js',{headers:{Range:'bytes=0-9'}}],
 ['same-scope API','api/document?id=fixture',{}],
 ['case JSON','case.json',{}],
 ['unrecognized version','app.js?v=future',{}],
 ['query-bearing static request','model.js?case=fixture',{}],
 ['worker source','sw.js',{}]
])test(`${name} is not intercepted or newly cached`,async()=>{
 const h=harness({seed:seed(path)});const e=h.dispatch(path,options);assert.equal(e.response,undefined);assert.equal(e.waits.length,0);assert.equal(h.calls.fetch.length,0);assert.equal(h.calls.open.length,0);
});
for(const [name,flags] of [['cache unavailable',{openError:true}],['cache lookup failure',{matchError:true}],['cache write failure',{putError:true}]])test(`${name} does not break a healthy network response`,async()=>{
 const h=harness({...flags,fetchImpl:()=>Promise.resolve(hit('fresh'))});const e=h.dispatch();assert.equal(await (await e.response).text(),'fresh');await e.settle();assert.equal(h.timers.size,0);
});
test('successful install precaches exactly the existing shell and then skips waiting',async()=>{
 const h=harness();await h.lifecycle('install');assert.deepEqual(Array.from(h.calls.add[0]),ASSETS.map(p=>'./'+p));assert.equal(h.calls.skip,1);
});
test('failed installation never skips waiting or deletes old caches',async()=>{
 const h=harness({seed:seed(),other:{'ippatsu-ledger-v2-old':seed()},installError:true});await assert.rejects(h.lifecycle('install'),/partial install/);assert.equal(h.calls.skip,0);assert.equal(h.calls.deleted.length,0);assert.equal(await h.body('app.js'),'cached');
});
test('activation removes only obsolete ledger caches and awaits client claim',async()=>{
 const h=harness({other:{'ippatsu-ledger-v2-old':seed(),unrelated:seed()}});await h.lifecycle('activate');assert.deepEqual(h.calls.deleted,['ippatsu-ledger-v2-old']);assert.equal(h.stores.has(CACHE),true);assert.equal(h.stores.has('unrelated'),true);assert.equal(h.calls.claim,1);
});
for(const [name,fn] of tests){await fn();console.log('PASS '+name);}
console.log(`ledger-v2 service worker: ${tests.length} tests passed`);
