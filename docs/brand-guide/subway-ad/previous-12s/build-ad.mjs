import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
const out=path.dirname(fileURLToPath(import.meta.url));
const root=path.resolve(out,'../../..');
const guide=await fs.readFile(path.join(root,'BenchMate_Brand_Guide.html'),'utf8');
const data=guide.match(/<script type="application\/json" id="construction-vector-data">([\s\S]*?)<\/script>/)[1];
const motion=guide.slice(guide.indexOf('<script>(() => {\n  const slide=')).replace(/^<script>/,'').split('</script>')[0];
if(!motion.includes('window.benchmateConstruction'))throw Error('Construction animation not found');
const font=(await fs.readFile(path.join(out,'../assets/SpaceGrotesk.ttf'))).toString('base64');
const html=`<!doctype html><html lang="en"><meta charset="utf-8"><title>BenchMate — Subway Ad</title>
<style>
@font-face{font-family:Space;src:url(data:font/ttf;base64,${font}) format('truetype');font-weight:300 700}
*{box-sizing:border-box}html,body{margin:0;width:100%;height:100%;overflow:hidden;background:#F3F4F8}
#ad{width:4114px;height:780px;position:absolute;transform-origin:top left;background:#F3F4F8;color:#3155D9}
#marks{position:absolute;inset:0}svg{display:block;width:100%;height:100%;overflow:visible}
#symbol-construction{position:absolute;left:105px;top:92px;width:596px;height:596px}
#wordmark-construction{position:absolute;left:750px;top:230px;width:1690px;height:282px}
.copy{position:absolute;left:2660px;top:239px;margin:0;font:500 112px/1.22 Space,sans-serif;letter-spacing:-4px}
.rule{position:absolute;left:2550px;top:220px;width:2px;height:340px;background:#3155D9;opacity:.23}
.accent{position:absolute;left:2664px;top:575px;width:110px;height:12px;background:#D6E879}
#controls{display:none}
</style>
<main id="ad" aria-label="BenchMate. Guided projects. From idea to made.">
<div id="marks"><div id="symbol-construction"></div><div id="wordmark-construction"></div></div>
<div class="rule"></div><p class="copy">Guided projects.<br>From idea to made.</p><div class="accent"></div>
</main>
<div id="controls"><div id="slide-logo" hidden></div><input id="construction-scrub"><button id="construction-play"><svg><path id="construction-play-icon"/></svg></button><button id="construction-replay"></button></div>
<script type="application/json" id="construction-vector-data">${data}</script>
<script>${motion}</script>
<script>
const duration=12;let manual=false;
function fit(){document.getElementById('ad').style.transform='scale('+Math.min(innerWidth/4114,innerHeight/780)+')'}addEventListener('resize',fit);fit();
window.renderAd=t=>{manual=true;const phase=Math.min(t,10)/10;window.benchmateConstruction.seek(phase);document.getElementById('marks').style.opacity=t>11.4?Math.max(0,(12-t)/.6):1;};
const start=performance.now();function tick(now){if(!manual){const t=((now-start)/1000)%duration;window.benchmateConstruction.seek(Math.min(t,10)/10);document.getElementById('marks').style.opacity=t>11.4?Math.max(0,(12-t)/.6):1;}requestAnimationFrame(tick)}requestAnimationFrame(tick);
</script></html>`;
await fs.writeFile(path.join(out,'ad.html'),html);
await fs.writeFile(path.join(out,'source-vectors.json'),data);
console.log('Created exact-size ad from current guide vectors and motion');
