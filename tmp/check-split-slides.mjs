import {chromium} from '@playwright/test';
import assert from 'node:assert/strict';
const browser=await chromium.launch({channel:'msedge'});
const page=await browser.newPage({viewport:{width:1640,height:1000}});
const errors=[];page.on('pageerror',e=>errors.push(e.message));
await page.goto('http://127.0.0.1:8789/#11');
await page.evaluate(()=>document.fonts.ready);
assert.equal(await page.locator('.slide').count(),13);
assert.equal(await page.locator('#slide-business-logic .logic-wedge').count(),0);
for(const n of [11,12,13]){
  assert.ok((await page.locator('#count').innerText()).includes(`${n} of 13`));
  await page.screenshot({path:`docs/evidence/maker-day-2/split-slide-${n}.png`});
  console.log(JSON.stringify(await page.locator('.slide:visible').evaluate(s=>({title:s.dataset.title,overflow:[...s.querySelectorAll('h1,h2,h3,p')].filter(e=>e.scrollWidth>e.clientWidth+2).map(e=>e.textContent)}))));
  if(n<13)await page.getByRole('button',{name:'Next slide'}).click();
}
assert.deepEqual(errors,[]);
await browser.close();

