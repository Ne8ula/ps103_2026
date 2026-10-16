import fs from 'node:fs';
import http from 'node:http';
import assert from 'node:assert/strict';
import {chromium} from '@playwright/test';
const server=http.createServer((q,r)=>{r.setHeader('Content-Type','text/html; charset=utf-8');r.end(fs.readFileSync('sites/benchmate-maker-day-2/dist/index.html'));});
await new Promise(resolve=>server.listen(8794,'127.0.0.1',resolve));
const browser=await chromium.launch({channel:'msedge'});
try{
 const p=await browser.newPage({viewport:{width:1640,height:1000}});
 await p.goto('http://127.0.0.1:8794/#6');await p.evaluate(()=>document.fonts.ready);
 assert.equal(await p.locator('.slide:visible').getAttribute('id'),'slide-differentiation');
 const overflow=await p.locator('#slide-differentiation').evaluate(s=>[...s.querySelectorAll('h1,h2,h3,p')].filter(e=>e.scrollWidth>e.clientWidth+1).map(e=>e.textContent));
 assert.deepEqual(overflow,[]);
 await p.screenshot({path:'docs/evidence/maker-day-2/simplified-differentiation.png'});
 console.log('Slide 6 checked; no text overflow.');
}finally{await browser.close();server.close();}
