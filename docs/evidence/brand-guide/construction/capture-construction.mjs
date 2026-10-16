import {chromium} from '@playwright/test';
import {spawn} from 'node:child_process';
import {once} from 'node:events';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
const browser=await chromium.launch({channel:'msedge'});
const page=await browser.newPage({viewport:{width:1636,height:1000},offline:true,reducedMotion:'reduce'});
await page.goto(pathToFileURL(path.resolve('BenchMate_Brand_Guide.html')).href+'#2');await page.evaluate(()=>document.fonts.ready);
const encoder=spawn('ffmpeg',['-hide_banner','-loglevel','error','-y','-f','image2pipe','-framerate','24','-i','pipe:0','-c:v','libx264','-crf','18','-pix_fmt','yuv420p','-movflags','+faststart','docs/brand-guide/BenchMate-Construction.mp4'],{windowsHide:true});
let failure='';encoder.stderr.on('data',d=>failure+=d);const complete=once(encoder,'close');
for(let frame=0;frame<252;frame++){
  await page.evaluate(value=>benchmateConstruction.seek(value),Math.min(1,frame/240));
  const image=await page.locator('#slide-logo').screenshot();
  if(!encoder.stdin.write(image))await once(encoder.stdin,'drain');
}
encoder.stdin.end();const[code]=await complete;if(code)throw Error(failure);
await browser.close();console.log('Saved 10.5-second construction preview at 24 fps');
