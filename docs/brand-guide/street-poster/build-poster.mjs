import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {chromium} from '@playwright/test';
const out=path.dirname(fileURLToPath(import.meta.url));
const assets=path.resolve(out,'../assets');
const embed=async(name,type='image/svg+xml')=>`data:${type};base64,${(await fs.readFile(path.join(assets,name))).toString('base64')}`;
const vectors=JSON.parse(await fs.readFile(path.join(out,'../subway-ad/source-vectors.json'),'utf8'));
const uri=s=>'data:image/svg+xml;base64,'+Buffer.from(s).toString('base64');
const font=await embed('SpaceGrotesk.ttf','font/ttf');
const ribbon=await embed('dither-ribbons.svg'),orbit=await embed('dither-orbit.svg'),facets=await embed('dither-facets.svg');
const html=`<!doctype html><html lang="en"><meta charset="utf-8"><title>BenchMate — Street Poster</title>
<style>@font-face{font-family:Space;src:url(${font}) format('truetype');font-weight:300 700}*{box-sizing:border-box}html,body{margin:0;background:#F3F4F8;width:1800px;height:1125px;overflow:hidden}main{width:1800px;height:1125px;position:relative;overflow:hidden;color:#3155D9;background:#F3F4F8}.logo{position:absolute;left:55px;top:68px;width:240px;height:240px}.wordmark{position:absolute;left:325px;top:90px;width:1360px;height:227px}h1{position:absolute;left:105px;top:398px;margin:0;font:500 106px/1.12 Space,sans-serif;letter-spacing:-5px;z-index:2}.lime{position:absolute;left:108px;top:710px;width:125px;height:14px;background:#D6E879}.orbit{position:absolute;width:800px;height:440px;right:-50px;top:380px;object-fit:contain;transform:rotate(-8deg)}.ribbon{position:absolute;left:-70px;bottom:-410px;width:1950px;height:836px;object-fit:contain}.small{position:absolute;left:108px;top:815px;margin:0;font:400 31px/1.4 Space,sans-serif;letter-spacing:-.5px;color:#292733;z-index:3}.rule{position:absolute;left:108px;right:108px;top:348px;height:1px;background:#3155D9;opacity:.15}</style>
<main><img class="logo" src="${uri(vectors.logo)}" alt="BenchMate symbol"><img class="wordmark" src="${uri(vectors.wordmark)}" alt="BenchMate"><div class="rule"></div><h1>Guided projects.<br>From idea to made.</h1><div class="lime"></div><img class="orbit" src="${facets}" alt=""><img class="ribbon" src="${ribbon}" alt=""></main></html>`;
await fs.writeFile(path.join(out,'poster.html'),html);
const board=`<html><body style="margin:0;background:#F3F4F8">${[ribbon,orbit,facets].map((s,i)=>`<div style="height:280px"><b>${['Ribbons','Orbit','Facets'][i]}</b><img src="${s}" style="width:900px;height:250px;display:block"></div>`).join('')}</body></html>`;
const browser=await chromium.launch({headless:true,executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe'});
const p=await browser.newPage({viewport:{width:1800,height:1125},deviceScaleFactor:2});
await p.goto(pathToFileURL(path.join(out,'poster.html')).href);await p.evaluate(()=>document.fonts.ready);await p.screenshot({path:path.join(out,'BenchMate-Street-Poster.png')});
await p.setViewportSize({width:1000,height:850});await p.setContent(board);await p.screenshot({path:path.join(out,'graphics-reference.png')});
await browser.close();console.log('Rendered poster and graphics reference');
