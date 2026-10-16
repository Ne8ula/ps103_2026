import fs from 'node:fs';
import http from 'node:http';
import assert from 'node:assert/strict';
import {chromium} from '@playwright/test';
const server=http.createServer((q,r)=>{r.setHeader('Content-Type','text/html; charset=utf-8');r.end(fs.readFileSync('sites/benchmate-maker-day-2/dist/index.html'));});
await new Promise(resolve=>server.listen(8792,'127.0.0.1',resolve));
const browser=await chromium.launch({channel:'msedge'});
try{
 const page=await browser.newPage({viewport:{width:1640,height:1000}});
 for(const n of [5,10,11]){
  await page.goto(`http://127.0.0.1:8792/?check=${n}#${n}`);
  await page.evaluate(()=>document.fonts.ready);
  assert.equal(await page.locator('.slide').count(),14);
  if(n===5){assert.ok((await page.locator('.technical-stack').innerText()).includes('GestLLM'));assert.ok(await page.locator('.technical-stack').evaluate(e=>e.scrollWidth<=e.clientWidth));}
  if(n===10)assert.equal(await page.locator('.stack-parts > div:nth-child(2) h3').evaluate(e=>getComputedStyle(e).backgroundColor),'rgba(0, 0, 0, 0)');
  if(n===11){assert.equal(await page.locator('.finance-highlight dd').innerText(),'$18K');assert.equal(await page.locator('.finance-metrics > div:nth-child(3)').evaluate(e=>getComputedStyle(e).backgroundColor),'rgba(0, 0, 0, 0)');}
  await page.screenshot({path:`docs/evidence/maker-day-2/stack-highlight-${n}.png`});
 }
 console.log('Slides 5, 10, 11 checked: stack fits; GestLLM unhighlighted; $18K highlighted.');
}finally{await browser.close();server.close();}
