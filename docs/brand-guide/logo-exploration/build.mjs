import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { chromium } from '@playwright/test';

const dir = path.dirname(fileURLToPath(import.meta.url));
const concepts = [
  { id:'01-workbench', name:'The Workbench', idea:'A place to make.', description:'A block above a sturdy bench. The open centre gives the mark a welcoming, workshop-like silhouette.', note:'The clearest link to BenchMate.', shapes:'<path d="M48 104H208V144H184V208H144V144H104V208H64V144H48Z"/><rect x="104" y="48" width="48" height="40" rx="4"/>' },
  { id:'02-join', name:'The Joint', idea:'Parts become a project.', description:'Two stepped pieces fit around a shared opening. A small nod to joinery, assembly and a companion working with you.', note:'The closest to your abstract references.', shapes:'<path d="M48 48H144V88H88V112H112V152H48Z"/><path d="M208 208H112V168H168V144H144V104H208Z"/>' },
  { id:'03-helping-hand', name:'The Helping Hand', idea:'Learn with your hands.', description:'A pixel palm supports one square piece. It turns “Your Ideas, A Helping Hand” into a compact symbol.', note:'The strongest expression of the promise.', shapes:'<rect x="120" y="48" width="48" height="48" rx="4"/><path d="M48 112H80V144H176V112H208V160H184V184H160V208H96V184H72V160H48Z"/>' },
  { id:'04-built-b', name:'The Built B', idea:'An initial, assembled.', description:'A stepped B with two open bays and an offset building block. Echoes the pixel B already in the wordmark.', note:'The strongest typographic family resemblance.', shapes:'<path fill-rule="evenodd" d="M56 48H144V88H184V112H208V184H184V208H56Z M96 88V112H144V88Z M96 152V176H168V152Z"/><rect x="160" y="40" width="48" height="32"/>' },
  { id:'05-maker-m', name:'The Maker M', idea:'Build your own way.', description:'Two upright supports and a stepped centre create an M. A small bridge between making, structure and BenchMate.', note:'The boldest compact monogram.', shapes:'<path d="M48 208V48H88V88H112V112H144V88H168V48H208V208H168V144H144V168H112V144H88V208Z"/>' },
];

await fs.mkdir(dir,{recursive:true});
const svg = (c, color='#3155D9', background='') => `<svg xmlns="http://www.w3.org/2000/svg" width="1024" height="1024" viewBox="0 0 256 256" role="img" aria-label="${c.name}"><title>BenchMate / ${c.name}</title>${background ? `<path fill="${background}" d="M0 0H256V256H0Z"/>` : ''}<g fill="${color}">${c.shapes}</g></svg>`;
for(const c of concepts) await fs.writeFile(path.join(dir,`${c.id}.svg`),svg(c));
await fs.writeFile(path.join(dir,'concepts.json'), JSON.stringify({source:'BenchMate_Brand_Guide.html, Branding Guide 0.5',method:'Original SVG geometry, rendered to PNG with Chromium. No generative-image model used.',colors:{blue:'#3155D9',lime:'#D6E879',cloud:'#F3F4F8',ink:'#292733'},concepts},null,2));

const html = `<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>BenchMate — Five marks for making</title><style>
@font-face{font-family:Grotesk;src:url('../assets/SpaceGrotesk.ttf')}@font-face{font-family:Mono;src:url('../assets/SpaceMono-Regular.ttf')}@font-face{font-family:Pixel;src:url('../assets/Silkscreen-Regular.ttf')}
*{box-sizing:border-box}body{margin:0;background:#FCFCFE;color:#292733;font-family:Grotesk,Arial,sans-serif}main{max-width:1640px;margin:auto;padding:52px 54px 36px}header{display:flex;align-items:flex-start;justify-content:space-between;gap:30px;margin-bottom:36px}.eyebrow{font:12px Mono,monospace;color:#3155D9;margin:0 0 13px}h1{font-size:44px;letter-spacing:-1.8px;line-height:1.1;margin:0}header p{font:13px/1.7 Mono,monospace;max-width:390px;margin:0;color:#5E6270}.grid{display:grid;grid-template-columns:repeat(3,1fr);gap:28px 32px}.concept{min-width:0;border-top:1px solid #D9DBE2;padding-top:15px}.title{display:flex;align-items:baseline;gap:13px}.num{font:12px Pixel,monospace;color:#3155D9}h2{font-size:22px;letter-spacing:-.6px;font-weight:500;margin:0}.hero{height:226px;background:#F3F4F8;display:grid;place-items:center;margin:14px 0 0}.hero svg{width:226px;height:226px}.lockup{display:flex;align-items:center;justify-content:center;gap:14px;height:65px;border-bottom:1px solid #E5E6EE}.lockup svg{width:43px;height:43px}.wordmark{width:220px;height:auto}.specimens{display:flex;align-items:center;gap:12px;margin:13px 0}.chip{width:42px;height:42px;display:grid;place-items:center;background:#292733}.chip svg{width:40px;height:40px}.chip.lime{background:#D6E879}.small{display:flex;align-items:center;gap:10px;margin-left:auto;color:#5E6270;font:10px Mono}.small svg{width:24px;height:24px}.description{font:12px/1.7 Mono,monospace;margin:0;color:#5E6270;min-height:62px}.idea{font-weight:500;font-size:16px;margin:11px 0 5px}.links{display:flex;gap:18px;margin-top:10px}a{font:10px Mono;color:#3155D9;text-underline-offset:3px}a:focus-visible{outline:2px solid #3155D9;outline-offset:4px}.direction{padding:25px 28px;border-top:1px solid #D9DBE2;background:#F3F8D7;display:flex;flex-direction:column;justify-content:space-between}.direction img{width:100%;max-width:330px;margin:34px 0}.direction h2{font-size:29px;line-height:1.16;letter-spacing:-1px}.direction p{font:12px/1.8 Mono;color:#514D63;max-width:355px}.direction strong{color:#292733;font-weight:400}.direction .eyebrow{color:#5E6927}footer{display:flex;justify-content:space-between;border-top:1px solid #D9DBE2;margin-top:30px;padding-top:16px;font:10px Mono;color:#5E6270}.swatches{display:flex;gap:5px;margin-top:12px}.swatches span{width:25px;height:6px;background:var(--c)}
@media(max-width:1000px){main{padding:32px}.grid{grid-template-columns:repeat(2,1fr)}header{display:block}header p{margin-top:20px;max-width:600px}}@media(max-width:620px){main{padding:26px 20px}.grid{grid-template-columns:1fr}h1{font-size:35px}header{margin-bottom:26px}.hero{height:260px}.hero svg{width:250px;height:250px}.description{min-height:0}.direction{min-height:350px}footer{gap:20px;line-height:1.6}}
</style><main><header><div><p class="eyebrow">BENCHMATE / LOGO EXPLORATION 01</p><h1>Five marks for making.</h1></div><p>Solid shapes. A little pixel character.<br>Five square symbols, paired with your existing wordmark. Choose the idea first; refine the geometry next.</p></header><div class="grid">${concepts.map((c,i)=>`<article class="concept"><div class="title"><span class="num">0${i+1}</span><h2>${c.name}</h2></div><div class="hero">${svg(c)}</div><div class="lockup">${svg(c)}<img class="wordmark" src="../assets/benchmate-wordmark.svg" alt="BenchMate"></div><div class="specimens"><span class="chip">${svg(c,'#FFFFFF')}</span><span class="chip lime">${svg(c,'#292733')}</span><span class="small">24 px ${svg(c,'#292733')}</span></div><p class="idea">${c.idea}</p><p class="description">${c.description}</p><div class="links"><a href="${c.id}.svg" download>SVG / editable</a><a href="${c.id}.png" download>PNG / 1024 square</a></div></article>`).join('')}<aside class="direction"><div><p class="eyebrow">SAME FAMILY. NEW SYMBOL.</p><img src="../assets/benchmate-wordmark.svg" alt="Existing BenchMate wordmark"><h2>A quiet companion<br>to expressive type.</h2><p>The wordmark already mixes geometric, serif and pixel forms. These symbols use a single colour, generous openings and a coarse grid to sit comfortably beside it.</p></div><div><p><strong>Start with 02 for abstract assembly,<br>or 03 for the helping-hand story.</strong></p><div class="swatches"><span style="--c:#3155D9"></span><span style="--c:#D6E879"></span><span style="--c:#292733"></span></div></div></aside></div><footer><span>BRANDING GUIDE 0.5 / EXPLORATORY CONCEPTS</span><span>ORIGINAL VECTOR MARKS · 1024 × 1024 EXPORTS</span></footer></main></html>`;
await fs.writeFile(path.join(dir,'index.html'),html);
const browser=await chromium.launch({headless:true,channel:'chrome'});
try {
  const page=await browser.newPage({viewport:{width:1600,height:1400},deviceScaleFactor:1});
  await page.goto(pathToFileURL(path.resolve(dir,'../../../BenchMate_Brand_Guide.html')).href);
  await page.evaluate(()=>document.fonts.ready);
  await page.screenshot({path:path.join(dir,'source-guide.png')});
  await page.goto(pathToFileURL(path.join(dir,'index.html')).href);
  await page.evaluate(()=>document.fonts.ready);
  await page.screenshot({path:path.join(dir,'comparison.png'),fullPage:true});
  await page.setViewportSize({width:393,height:852});
  await page.screenshot({path:path.join(dir,'mobile-preview.png'),fullPage:true});
  const mobileOverflow=await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth);
  const brokenImages=await page.locator('img').evaluateAll(imgs=>imgs.filter(i=>!i.complete||i.naturalWidth===0).length);
  await page.setViewportSize({width:1024,height:1024});
  for (const c of concepts) {
    await page.setContent(`<style>html,body{margin:0;width:1024px;height:1024px}svg{display:block}</style>${svg(c,'#3155D9','#F3F4F8')}`);
    await page.screenshot({path:path.join(dir,`${c.id}.png`)});
    await page.setContent(`<style>html,body{margin:0;width:1024px;height:1024px}svg{display:block}</style>${svg(c)}`);
    await page.screenshot({path:path.join(dir,`${c.id}-transparent.png`),omitBackground:true});
  }
  console.log(JSON.stringify({output:dir,concepts:concepts.length,mobileOverflow,brokenImages}));
} finally {await browser.close();}
