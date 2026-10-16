import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {chromium} from '@playwright/test';

const dir=path.dirname(fileURLToPath(import.meta.url));
const concepts=[
 {id:'01-soft-workbench',name:'Soft Workbench',idea:'The familiar bench, a little warmer.',description:'Keeps the original silhouette and floating project block. Small corner radii soften the sturdy pixel construction.',shapes:'<path d="M56 104H200Q208 104 208 112V144H192V200Q192 208 184 208H152V152Q152 144 144 144H112Q104 144 104 152V208H72Q64 208 64 200V144H48V112Q48 104 56 104Z"/><rect x="104" y="48" width="48" height="40" rx="8"/>'},
 {id:'02-piece-in-place',name:'Piece in Place',idea:'One piece away from making it yours.',description:'An offset block lines up with a recess in the worktop. The bench becomes a little project being assembled.',shapes:'<rect x="136" y="48" width="48" height="40"/><path d="M48 112H136V136H184V112H208V152H192V208H152V168H104V208H64V152H48Z"/>'},
 {id:'03-soft-joint',name:'Soft Joint',idea:'Two parts, one partnership.',description:'The original interlocking rhythm with rounded outer corners and softened notches. Closest to the rounded reference marks.',shapes:'<path d="M64 48H136Q144 48 144 56V88H96Q88 88 88 96V104Q88 112 96 112H112V144Q112 152 104 152H48V64Q48 48 64 48Z"/><path d="M192 208H120Q112 208 112 200V168H160Q168 168 168 160V152Q168 144 160 144H144V112Q144 104 152 104H208V192Q208 208 192 208Z"/>'},
 {id:'04-close-fit',name:'Close Fit',idea:'A satisfying fit.',description:'Two complementary pieces form a compact square. A stepped seam keeps the join visible in a single colour.',shapes:'<path d="M64 48H120V96H160V128H120V160H48V64Q48 48 64 48Z"/><path d="M136 48H192Q208 48 208 64V192Q208 208 192 208H64Q48 208 48 192V176H136V144H176V80H136Z"/>'},
 {id:'05-joined-workbench',name:'Joined Workbench',idea:'A bench built from two parts.',description:'Combines the workbench silhouette with a stepped joint. The seam makes collaboration part of the structure itself.',shapes:'<rect x="104" y="48" width="48" height="40" rx="4"/><path d="M56 104H112V120H136V136H112V152H104V208H72Q64 208 64 200V144H48V112Q48 104 56 104Z"/><path d="M128 104H200Q208 104 208 112V144H192V200Q192 208 184 208H152V152H128V148H148V108H128Z"/>'},
];
const svg=(c,color='#3155D9',bg='')=>`<svg xmlns="http://www.w3.org/2000/svg" width="1024" height="1024" viewBox="0 0 256 256" role="img" aria-label="${c.name}"><title>BenchMate / ${c.name}</title>${bg?`<path fill="${bg}" d="M0 0H256V256H0Z"/>`:''}<g fill="${color}">${c.shapes}</g></svg>`;
await fs.mkdir(dir,{recursive:true});
for(const c of concepts)await fs.writeFile(path.join(dir,c.id+'.svg'),svg(c));
await fs.writeFile(path.join(dir,'concepts.json'),JSON.stringify({round:2,parents:['01-workbench','02-join'],method:'Original SVG variations, rendered with Chromium.',concepts},null,2));
const previous=await fs.readFile(path.resolve(dir,'../logo-exploration/index.html'),'utf8');
const styles=previous.match(/<style>([\s\S]*?)<\/style>/)[1];
const cards=concepts.map((c,i)=>`<article class="concept"><div class="title"><span class="num">0${i+1}</span><h2>${c.name}</h2></div><div class="hero">${svg(c)}</div><div class="lockup">${svg(c)}<img class="wordmark" src="../assets/benchmate-wordmark.svg" alt="BenchMate"></div><div class="specimens"><span class="chip">${svg(c,'#FFFFFF')}</span><span class="chip lime">${svg(c,'#292733')}</span><span class="small">24 px ${svg(c,'#292733')}</span></div><p class="idea">${c.idea}</p><p class="description">${c.description}</p><div class="links"><a href="${c.id}.svg" download>SVG</a><a href="${c.id}.png" download>1024 PNG</a><a href="${c.id}-transparent.png" download>Transparent PNG</a></div></article>`).join('');
const html=`<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>BenchMate — Workbench + Joint, round two</title><style>${styles}</style><main><header><div><p class="eyebrow">BENCHMATE / LOGO EXPLORATION 02</p><h1>Workbench + Joint.</h1></div><p>Five variations on your two favourites.<br>Two benches, two joints and one combination. Same wordmark. Same colour. A closer look at shape.</p></header><div class="grid">${cards}<aside class="direction"><div><p class="eyebrow">TWO IDEAS, TAKING SHAPE.</p><img src="../assets/benchmate-wordmark.svg" alt="BenchMate"><h2>Making things.<br>Fitting together.</h2><p>01–02 develop the workbench.<br>03–04 develop the joint.<br>05 combines both directions.</p><p>Each mark keeps the coarse pixel grid, solid silhouette and generous negative space of the first round.</p></div><div><p><strong>01 is the clearest continuation.<br>03 brings the softer reference style.<br>05 connects both stories.</strong></p><a href="../logo-exploration/index.html">Compare with round one →</a><div class="swatches"><span style="--c:#3155D9"></span><span style="--c:#D6E879"></span><span style="--c:#292733"></span></div></div></aside></div><footer><span>ROUND 02 / WORKBENCH + JOINT VARIATIONS</span><span>EDITABLE VECTORS · 1024 × 1024 EXPORTS</span></footer></main></html>`;
await fs.writeFile(path.join(dir,'index.html'),html);
const browser=await chromium.launch({headless:true,channel:'chrome'});
try{
 const page=await browser.newPage({viewport:{width:1600,height:1400},deviceScaleFactor:1});
 await page.goto(pathToFileURL(path.join(dir,'index.html')).href);
 await page.evaluate(()=>document.fonts.ready);
 await page.screenshot({path:path.join(dir,'comparison.png'),fullPage:true});
 await page.setViewportSize({width:393,height:852});
 await page.screenshot({path:path.join(dir,'mobile-preview.png'),fullPage:true});
 const checks=await page.evaluate(()=>({overflow:document.documentElement.scrollWidth>innerWidth,brokenImages:[...document.images].filter(i=>!i.complete||!i.naturalWidth).length,cards:document.querySelectorAll('.concept').length}));
 await page.setViewportSize({width:1024,height:1024});
 for(const c of concepts){
  for(const transparent of [false,true]){
   await page.setContent(`<style>html,body{margin:0;width:1024px;height:1024px}svg{display:block}</style>${svg(c,'#3155D9',transparent?'':'#F3F4F8')}`);
   await page.screenshot({path:path.join(dir,c.id+(transparent?'-transparent':'')+'.png'),omitBackground:transparent});
  }
 }
 console.log(JSON.stringify({output:dir,...checks}));
}finally{await browser.close()}
