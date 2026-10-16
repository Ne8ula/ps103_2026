import fs from 'node:fs';
import http from 'node:http';
import assert from 'node:assert/strict';
import {chromium} from '@playwright/test';
const server=http.createServer((q,r)=>{r.setHeader('Content-Type','text/html; charset=utf-8');r.end(fs.readFileSync('sites/benchmate-maker-day-2/dist/index.html'));});
await new Promise(resolve=>server.listen(8793,'127.0.0.1',resolve));
const browser=await chromium.launch({channel:'msedge'});
try{
 const p=await browser.newPage({viewport:{width:1640,height:1000}});
 await p.goto('http://127.0.0.1:8793/#4');await p.evaluate(()=>document.fonts.ready);
 assert.equal(await p.locator('.slide:visible').getAttribute('id'),'slide-how-it-works');
 const bounds=await p.evaluate(()=>{const org=document.querySelector('.organization-priorities');const learning=document.querySelector('.workflow-benefits');const footer=document.querySelector('#slide-how-it-works .foot');return {below:org.getBoundingClientRect().top>learning.getBoundingClientRect().bottom,aboveFooter:org.getBoundingClientRect().bottom<footer.getBoundingClientRect().top,overflow:[...document.querySelectorAll('#slide-how-it-works h1,#slide-how-it-works h2,#slide-how-it-works li')].filter(e=>e.scrollWidth>e.clientWidth+1).map(e=>e.textContent)};});
 assert.ok(bounds.below&&bounds.aboveFooter);assert.deepEqual(bounds.overflow,[]);
 await p.screenshot({path:'docs/evidence/maker-day-2/organization-priorities.png'});
 console.log(JSON.stringify(bounds));
}finally{await browser.close();server.close();}
