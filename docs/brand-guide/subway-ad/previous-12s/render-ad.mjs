import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {spawn} from 'node:child_process';
import {once} from 'node:events';
import {chromium} from '@playwright/test';
const out=path.dirname(fileURLToPath(import.meta.url));
const preview=process.argv.includes('--preview');
const browser=await chromium.launch({headless:true,executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe'});
const page=await browser.newPage({viewport:{width:4114,height:780},deviceScaleFactor:1});
const errors=[];page.on('pageerror',e=>errors.push(e.message));
await page.goto(pathToFileURL(path.join(out,'ad.html')).href);await page.evaluate(()=>document.fonts.ready);
if(preview){
 for(const t of [1.3,3.6,5,6.7,9]){await page.evaluate(t=>renderAd(t),t);await page.screenshot({path:path.join(out,`ad-${t}s.png`)});}
 console.log({errors});await browser.close();process.exit(errors.length?1:0);
}
const encoder=spawn('ffmpeg',['-y','-f','image2pipe','-vcodec','png','-framerate','30','-i','-','-an','-c:v','libx264','-preset','medium','-crf','17','-pix_fmt','yuv420p','-movflags','+faststart',path.join(out,'BenchMate-Ad-4114x780.mp4')],{stdio:['pipe','ignore','pipe']});
let log='';encoder.stderr.on('data',d=>log+=d);const finished=once(encoder,'close');
for(let i=0;i<360;i++){
 await page.evaluate(t=>renderAd(t),i/30);
 const frame=await page.screenshot();if(!encoder.stdin.write(frame))await once(encoder.stdin,'drain');
 if(i%60===0)console.log(`Rendered ${i}/360 frames`);
}
encoder.stdin.end();const [code]=await finished;await browser.close();
if(code||errors.length)throw Error(JSON.stringify({code,errors,log:log.slice(-2000)}));
console.log('Exported 12-second 30fps ad');
