import { chromium } from '@playwright/test';
import fs from 'node:fs';
import { pathToFileURL } from 'node:url';
import path from 'node:path';
const browser=await chromium.launch({channel:'msedge'});
const page=await browser.newPage({viewport:{width:1600,height:1000},offline:true});
const errors=[];page.on('pageerror',e=>errors.push(e.message));
await page.goto(pathToFileURL(path.resolve('BenchMate_Brand_Guide.html')).href);
await page.evaluate(()=>document.fonts.ready);
const checks={slides:[]};
for(let i=0;i<6;i++){
  if(i)await page.getByRole('button',{name:'Next slide'}).click();
  await page.evaluate(()=>document.fonts.ready);
  await page.screenshot({path:`docs/evidence/brand-guide/after-${['cover','motion','typography','color','walkthrough','mockups'][i]}.png`});
  checks.slides.push(await page.locator('.slide:visible').evaluate(slide=>{
    const overflow=[...slide.querySelectorAll('p,h1,h2,.alphabet,.weights,.usage,.type-column,.rule,.controls')].filter(e=>e.scrollWidth>e.clientWidth+1||e.scrollHeight>e.clientHeight+1).map(e=>({tag:e.tagName,class:e.className,text:e.textContent}));
    return {id:slide.id,overflow,images:[...slide.querySelectorAll('img')].every(e=>e.complete&&e.naturalWidth>0),heading:getComputedStyle(slide.querySelector('h1')).fontFamily,body:slide.querySelector('p')?getComputedStyle(slide.querySelector('p')).fontFamily:null};
  }));
}
checks.fonts=await page.evaluate(()=>[...document.fonts].map(f=>({family:f.family,weight:f.weight,status:f.status})));
const logo=fs.readFileSync('docs/brand-guide/assets/benchmate-wordmark.svg','utf8');
checks.identicalBBowls=logo.match(/id="b-upper-bowl" d="([^"]+)"/)[1]===logo.match(/id="b-lower-bowl" d="([^"]+)"/)[1];
checks.nextDisabled=await page.getByRole('button',{name:'Next slide'}).isDisabled();
await page.keyboard.press('Home');
checks.homeNavigation=await page.locator('#slide-0').isVisible();
await page.keyboard.press('End');
checks.endNavigation=await page.locator('#slide-mockups').isVisible();
await page.reload();checks.hashRestored=await page.locator('#slide-mockups').isVisible();
await page.setViewportSize({width:393,height:852});
await page.screenshot({path:'docs/evidence/brand-guide/after-phone.png'});
checks.phone=await page.evaluate(()=>({width:innerWidth,documentWidth:document.documentElement.scrollWidth}));
await page.emulateMedia({media:'print'});
checks.printSlideCount=await page.locator('.slide:visible').count();
checks.errors=errors;
fs.writeFileSync('docs/evidence/brand-guide/checks.json',JSON.stringify(checks,null,2));
console.log(JSON.stringify(checks,null,2));
await browser.close();
