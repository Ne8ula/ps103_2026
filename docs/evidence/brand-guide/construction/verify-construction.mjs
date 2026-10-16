import {chromium,expect} from '@playwright/test';
import fs from 'node:fs';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
const browser=await chromium.launch({channel:'msedge'});
const page=await browser.newPage({viewport:{width:1600,height:1000},offline:true,reducedMotion:'reduce'});
const errors=[];page.on('pageerror',e=>errors.push(e.message));
const url=pathToFileURL(path.resolve('BenchMate_Brand_Guide.html')).href;
await page.goto(url+'#1');await page.getByRole('button',{name:'Next slide'}).click();await page.evaluate(()=>document.fonts.ready);
const checks={reduced:await page.evaluate(()=>benchmateConstruction.getState()),phases:[]};
expect(checks.reduced.stage).toBe('Complete');expect(checks.reduced.playing).toBe(false);
expect((await page.locator('.construction-box').allTextContents()).map(text=>text.trim())).toEqual(['Wordmark','Logo']);
const dimensions=await page.locator('.construction-box').evaluateAll(boxes=>boxes.map(e=>({w:e.clientWidth,h:e.clientHeight})));
expect(dimensions[1].w).toBeLessThan(dimensions[0].w);expect(dimensions[1].h).toBeLessThan(dimensions[0].h);
checks.boxes=dimensions;
const sourcePaths=await page.evaluate(()=>{
 const vectors=JSON.parse(document.getElementById('construction-vector-data').textContent);
 return Object.fromEntries(Object.entries(vectors).map(([key,source])=>[key,[...new DOMParser().parseFromString(source,'image/svg+xml').querySelectorAll('path')].map(p=>({d:p.getAttribute('d'),transform:p.getAttribute('transform')}))]));
});
for(const [value,name] of [[.14,'blueprint'],[.37,'wireframe'],[.5,'details'],[.67,'colors'],[.9,'complete']]){
  await page.evaluate(v=>benchmateConstruction.seek(v),value);
  await page.screenshot({path:`docs/evidence/brand-guide/construction/${name}.png`});
  const phase=await page.evaluate(()=>benchmateConstruction.getState().stage);checks.phases.push(phase);
  for(const [selector,key]of [['wordmark','wordmark'],['symbol','logo']]){
    const actual=await page.locator(`#${selector}-construction [data-layer=colors] path`).evaluateAll(paths=>paths.map(p=>({d:p.getAttribute('d'),transform:p.getAttribute('transform')})));
    expect(actual).toEqual(sourcePaths[key]);
  }
}
checks.exactSourcePaths=true;
await page.getByRole('slider').focus();await page.keyboard.press('Home');await page.keyboard.press('ArrowRight');
expect(await page.locator('#slide-logo').isVisible()).toBe(true);expect(await page.evaluate(()=>benchmateConstruction.getState().position)).toBe(.001);
await page.getByRole('button',{name:'Play Construction Animation',exact:true}).click();
await expect.poll(()=>page.evaluate(()=>benchmateConstruction.getState().position)).toBeGreaterThan(.01);
await page.getByRole('button',{name:'Pause Construction Animation'}).click();
const frame=await page.evaluate(()=>benchmateConstruction.getState().renderCount);await page.waitForTimeout(100);
expect(await page.evaluate(()=>benchmateConstruction.getState().renderCount)).toBe(frame);
await page.getByRole('button',{name:'Replay Construction Animation'}).click();expect(await page.evaluate(()=>benchmateConstruction.getState().position)).toBeLessThan(.1);
await page.getByRole('button',{name:'Next slide'}).click();
const stopped=await page.evaluate(()=>benchmateConstruction.getState().renderCount);await page.waitForTimeout(100);
expect(await page.evaluate(()=>benchmateConstruction.getState().renderCount)).toBe(stopped);
await page.getByRole('button',{name:'Previous slide'}).click();
await expect.poll(()=>page.evaluate(()=>benchmateConstruction.getState().renderCount)).toBeGreaterThan(stopped);
checks.controls='Pause, replay, range keyboard control, and hidden-slide suspension passed';
await page.evaluate(()=>benchmateConstruction.seek(.9));
await page.setViewportSize({width:393,height:852});await page.screenshot({path:'docs/evidence/brand-guide/construction/phone.png'});
expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
await page.emulateMedia({media:'print'});expect(await page.locator('.construction-static:visible').count()).toBe(2);
expect(await page.locator('.construction-art:visible').count()).toBe(0);
checks.print='Both source vectors replace animated layers in print';
checks.errors=errors;expect(errors).toEqual([]);
fs.writeFileSync('docs/evidence/brand-guide/construction/checks.json',JSON.stringify(checks,null,2));
console.log(JSON.stringify(checks,null,2));await browser.close();
