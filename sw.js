const CACHE="jeepre-v2";
const CORE=["./","./index.html","./manifest.webmanifest","./icon.svg"];
self.addEventListener("install",event=>event.waitUntil((async()=>{const cache=await caches.open(CACHE);await cache.addAll(CORE);await self.skipWaiting()})()));
self.addEventListener("activate",event=>event.waitUntil((async()=>{const keys=await caches.keys();await Promise.all(keys.filter(key=>key!==CACHE).map(key=>caches.delete(key)));await self.clients.claim()})()));
self.addEventListener("fetch",event=>{
 const req=event.request;if(req.method!=="GET")return;
 const url=new URL(req.url);if(url.origin!==self.location.origin)return;
 const isPage=req.mode==="navigate"||req.destination==="document"||url.pathname.endsWith(".html");
 if(isPage){
  event.respondWith((async()=>{try{const fresh=await fetch(req,{cache:"no-store"});if(fresh.ok){const cache=await caches.open(CACHE);cache.put(req,fresh.clone());}return fresh}catch(error){return (await caches.match(req))||(await caches.match("./index.html"))}})());
 }else{
  event.respondWith((async()=>{const hit=await caches.match(req);if(hit)return hit;try{const fresh=await fetch(req);if(fresh.ok){const cache=await caches.open(CACHE);cache.put(req,fresh.clone())}return fresh}catch(error){return hit||Response.error()}})());
 }
});
