import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {chromium} from '@playwright/test';
const out=path.dirname(fileURLToPath(import.meta.url));
const assets=path.resolve(out,'../assets');
const embed=async(file,type)=>`data:${type};base64,${(await fs.readFile(file)).toString('base64')}`;
const svg=async name=>embed(path.join(assets,name),'image/svg+xml');
const vectors=JSON.parse(await fs.readFile(path.join(out,'../subway-ad/source-vectors.json'),'utf8'));
const uri=s=>'data:image/svg+xml;base64,'+Buffer.from(s).toString('base64');
const font=await embed(path.join(assets,'SpaceGrotesk.ttf'),'font/ttf');
const screenshot=await embed(path.join(out,'home-screen-original.png'),'image/png');
const ribbon=await svg('dither-ribbons.svg');
const html=`<!doctype html><html lang="en"><meta charset="utf-8"><title>BenchMate — Make Something</title>
<style>
@font-face{font-family:Space;src:url(${font}) format('truetype');font-weight:300 700}
*{box-sizing:border-box}html,body{margin:0;width:1800px;height:1800px;overflow:hidden;background:#F3F4F8}
main{position:relative;width:1800px;height:1800px;overflow:hidden;background:#F3F4F8;color:#3155D9}
.logo{position:absolute;left:60px;top:70px;width:240px;height:240px}
.wordmark{position:absolute;left:330px;top:100px;width:1350px;height:225px}
.rule{position:absolute;left:110px;right:110px;top:370px;height:2px;background:#3155D9;opacity:.15}
h1{position:absolute;left:110px;top:495px;margin:0;font:500 150px/1.04 Space,sans-serif;letter-spacing:-8px}
.copy{position:absolute;left:118px;top:905px;margin:0;font:400 66px/1.2 Space,sans-serif;letter-spacing:-2.5px}
.accent{position:absolute;left:120px;top:1130px;width:150px;height:15px;background:#D6E879}
.ribbon{position:absolute;left:-210px;bottom:-305px;width:2000px;height:857px;object-fit:contain}
.phone-shadow{position:absolute;left:1080px;top:470px;width:590px;height:1245.0839px;filter:drop-shadow(0 20px 20px rgba(32,36,70,.17));z-index:3}
/* Native layout clipping retains every source screen pixel. Crop only the exterior backdrop. */
.phone{position:absolute;width:417px;height:880px;transform:scale(1.4148681055);transform-origin:top left;overflow:hidden;border-radius:58px;background:#292733}
.phone img{position:absolute;left:-21px;top:-10px;width:461px;height:905px;max-width:none}
</style>
<main><img class="logo" src="${uri(vectors.logo)}" alt="BenchMate symbol"><img class="wordmark" src="${uri(vectors.wordmark)}" alt="BenchMate"><div class="rule"></div><h1>Make<br>something.</h1><p class="copy">Guided projects.<br>From idea to made.</p><div class="accent"></div><img class="ribbon" src="${ribbon}" alt=""><div class="phone-shadow"><div class="phone"><img src="${screenshot}" alt="Original BenchMate home screen displayed in an iPhone"></div></div></main></html>`;
await fs.writeFile(path.join(out,'poster.html'),html);
const browser=await chromium.launch({headless:true,executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe'});
const page=await browser.newPage({viewport:{width:1800,height:1800},deviceScaleFactor:2});
const errors=[];page.on('pageerror',e=>errors.push(e.message));
await page.goto(pathToFileURL(path.join(out,'poster.html')).href);await page.evaluate(()=>document.fonts.ready);
await page.screenshot({path:path.join(out,'BenchMate-Phone-Poster.png')});
await fs.writeFile(path.join(out,'production.json'),JSON.stringify({artworkSize:[3600,3600],layoutSize:[1800,1800],screenshot:'home-screen-original.png',screenshotSourceSize:[461,905],phoneWindow:{left:21,top:10,width:417,height:880,cornerRadius:58},screenTreatment:'Original screenshot embedded unchanged and clipped by native HTML layout to the phone silhouette. Generated cutout not used because it altered screen details.',pageErrors:errors},null,2));
await browser.close();if(errors.length)throw Error(JSON.stringify(errors));console.log('Rendered 3600 x 3600 poster using original screenshot');
