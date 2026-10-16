import {chromium} from '@playwright/test';
import fs from 'node:fs';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
import {spawn} from 'node:child_process';
import {once} from 'node:events';
const browser=await chromium.launch({channel:'msedge'});
const context=await browser.newContext({viewport:{width:1600,height:1000},reducedMotion:'no-preference',offline:true});
const page=await context.newPage();
await page.goto(pathToFileURL(path.resolve('BenchMate_Brand_Guide.html')).href+'#2');
await page.evaluate(()=>document.fonts.ready);
const playback=await page.evaluate(()=>new Promise(resolve=>{
  const start=performance.now(),samples=[];let previous=start;
  function sample(now){
    samples.push(now-previous);previous=now;
    if(now-start>=10200){
      samples.sort((a,b)=>a-b);
      resolve({durationMs:Math.round(now-start),frames:samples.length,medianFrameMs:samples[Math.floor(samples.length*.5)],p95FrameMs:samples[Math.floor(samples.length*.95)],state:benchmateLogoMotion.getState()});
    }else requestAnimationFrame(sample);
  }requestAnimationFrame(sample);
}));
fs.writeFileSync('docs/evidence/brand-guide/motion/playback.json',JSON.stringify(playback,null,2));
const encoder=spawn('ffmpeg',['-hide_banner','-loglevel','error','-y','-f','image2pipe','-framerate','30','-i','pipe:0','-c:v','libx264','-crf','18','-pix_fmt','yuv420p','-movflags','+faststart','docs/brand-guide/BenchMate-Wordmark-Motion.mp4'],{windowsHide:true});
let encoderError='';encoder.stderr.on('data',chunk=>encoderError+=chunk);
const complete=once(encoder,'close');
for(let frame=0;frame<300;frame++){
  const png=await page.evaluate(t=>{
    const p=t<1.5?0:t<4.2?(t-1.5)/2.7:t<5.8?1:t<8.7?1-(t-5.8)/2.9:0;
    benchmateLogoMotion.seek(p);
    const source=document.querySelector('#logo-motion-canvas');
    const out=document.createElement('canvas');out.width=source.width;out.height=source.height;
    const c=out.getContext('2d');c.fillStyle='#FCFDFF';c.fillRect(0,0,out.width,out.height);c.drawImage(source,0,0);
    return out.toDataURL('image/png').split(',')[1];
  },frame/30);
  if(!encoder.stdin.write(Buffer.from(png,'base64')))await once(encoder.stdin,'drain');
}
encoder.stdin.end();const [code]=await complete;if(code)throw Error(encoderError);
await context.close();
await browser.close();console.log(JSON.stringify(playback,null,2));
