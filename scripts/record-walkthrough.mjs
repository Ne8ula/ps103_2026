// Actual browser interactions with a capture-only caption overlay; app source is unchanged.
import {chromium,expect} from '@playwright/test';
import fs from 'node:fs/promises';
import {spawn} from 'node:child_process';
import {once} from 'node:events';
const out='docs/evidence/walkthrough',fps=30;
await fs.mkdir(out,{recursive:true});
const chapters=[
 {title:'Choose a project',duration:6,sentence:'Choose a project matched to your printer, avoiding tutorials that do not fit your equipment.',source:'VCA pp. 1, 4: VP1; Hauke and Yura on equipment-specific guidance.'},
 {title:'Prepare the project',duration:6,sentence:'Personalize your project and review the setup, bringing scattered printer and material details together.',source:'VCA pp. 4, 6: Yura on combining printer, slicer and filament settings.'},
 {title:'Check the printer',duration:7,sentence:'Check the plate and filament with visual guidance, making each preparation step easier to follow.',source:'VCA pp. 4, 6: Heki on visual steps and exact details; Yura on setup matching.'},
 {title:'Inspect the print',duration:6,sentence:'Inspect the first layer with a visual checklist, reducing guesswork about whether the print looks right.',source:'VCA pp. 6, 8: time lost to late failures; visible checkpoints. Intended benefit, not measured prevention.'},
 {title:'Finish the product',duration:8,sentence:'Follow cooling, removal, and final checks, so you know how to finish after printing ends.',source:'VCA pp. 1, 8–9: task-specific steps and visible checkpoints; applied here to the prototype finishing flow.'},
 {title:'Keep what you learned',duration:5,sentence:'Save your project and notes, keeping what you learned ready for your next attempt.',source:'VCA pp. 4, 7, 9: Kevin on repeated practice; saved progress and later reuse remain hypotheses to test.'},
];
const browser=await chromium.launch({channel:'msedge',headless:true,args:['--enable-unsafe-swiftshader']});
const context=await browser.newContext({viewport:{width:1600,height:1000},deviceScaleFactor:1,reducedMotion:'reduce'});
const page=await context.newPage(),errors=[];
page.on('pageerror',error=>errors.push(error.message));
const encoder=spawn('ffmpeg',['-hide_banner','-loglevel','error','-y','-f','image2pipe','-framerate',String(fps),'-i','pipe:0','-an','-c:v','libx264','-preset','medium','-crf','18','-pix_fmt','yuv420p','-movflags','+faststart',`${out}/BenchMate-Walkthrough.mp4`],{windowsHide:true});
let encoderError='';encoder.stderr.on('data',chunk=>encoderError+=chunk);
const finished=once(encoder,'close');
let frames=0,chapterStart=0,pointer={x:1440,y:860};
async function write(png,count){for(let i=0;i<count;i++){if(!encoder.stdin.write(png))await once(encoder.stdin,'drain');frames++;}}
async function hold(seconds){await write(await page.screenshot(),Math.round(seconds*fps));}
async function ready(){await page.evaluate(()=>document.fonts.ready);await page.waitForFunction(()=>![...document.querySelectorAll('[data-renderer]')].some(e=>e.dataset.renderer==='loading'));}
async function moveTo(locator){
 await locator.scrollIntoViewIfNeeded();const box=await locator.boundingBox();if(!box)throw Error('Target not visible');
 const target={x:box.x+box.width*.64,y:box.y+box.height*.5},start={...pointer};
 for(let i=1;i<=8;i++){const t=i/8,e=1-(1-t)**3;pointer={x:start.x+(target.x-start.x)*e,y:start.y+(target.y-start.y)*e};await page.evaluate(p=>{const c=document.querySelector('#walkthrough-cursor');c.style.left=p.x+'px';c.style.top=p.y+'px';},pointer);await write(await page.screenshot(),1);}
}
async function click(locator){
 await moveTo(locator);
 await page.evaluate(()=>document.querySelector('#walkthrough-cursor').classList.add('pressed'));await hold(.1);
 await locator.click();await ready();
 await page.evaluate(()=>document.querySelector('#walkthrough-cursor').classList.remove('pressed'));await hold(4/fps);
}
const button=name=>page.getByRole('button',{name,exact:true});
async function go(name){await click(button(name));}
async function fill(locator,text){await moveTo(locator);await locator.fill(text);await hold(7/fps);}
async function stage(index,action){
 chapterStart=frames;const c=chapters[index];c.start=frames/fps;
 await page.evaluate(({c,index})=>{
  document.querySelector('#walkthrough-stage').textContent=`0${index+1} / 06`;
  document.querySelector('#walkthrough-title').textContent=c.title;
  document.querySelector('#walkthrough-sentence').textContent=c.sentence;
  document.querySelectorAll('#walkthrough-progress i').forEach((el,i)=>el.className=i<=index?'done':'');
 },{c,index});
 await action();
 const remaining=c.duration*fps-(frames-chapterStart);if(remaining<0)throw Error(`Chapter ${index} exceeds budget`);
 await write(await page.screenshot(),remaining);c.end=frames/fps;
 await page.screenshot({path:`${out}/chapter-${index+1}.png`});
 console.log(`${index+1}/6: ${c.title} (${c.start}–${c.end}s)`);
}
try{
 await page.goto(process.env.BENCHMATE_URL||'http://127.0.0.1:4174');await ready();
 await expect(page.getByRole('heading',{name:'Make Something',exact:true,level:1})).toBeVisible();
 await page.addStyleTag({content:`
 .preview-detail{position:relative;align-self:center}
 #walkthrough-caption{width:320px;color:#292733}
 #walkthrough-caption .brand-logo{width:52px;height:52px;margin:0 0 30px}
 #walkthrough-stage{font:12px/1.5 'Silkscreen',monospace;color:#3155D9;margin-bottom:14px}
 #walkthrough-title{font:700 32px/1.2 'Space Grotesk',sans-serif;letter-spacing:-.8px;margin:0 0 20px;text-wrap:balance}
 #walkthrough-sentence{font:400 19px/1.65 'Space Mono',monospace;color:#514D63;text-wrap:pretty;margin:0}
 #walkthrough-progress{display:flex;gap:8px;margin-top:28px}
 #walkthrough-progress i{height:4px;flex:1;background:#CDD0DD;border-radius:2px}
 #walkthrough-progress i.done{background:#3155D9}
 #walkthrough-cursor{position:fixed;z-index:2147483647;pointer-events:none;width:22px;height:28px;left:1440px;top:860px;filter:drop-shadow(0 2px 2px #19182033)}
 #walkthrough-cursor::before{content:'';position:absolute;width:48px;height:48px;border-radius:50%;background:#3155d918;left:-18px;top:-18px;border:1px solid #3155d933}
 #walkthrough-cursor.pressed::before{background:#d6e87999;border:2px solid #3155D9}
 `});
 await page.evaluate(()=>{
  document.querySelector('.preview-detail').innerHTML='<div id="walkthrough-caption"><img class="brand-logo" src="/brand/benchmate-logo.svg" alt=""><div id="walkthrough-stage"></div><h2 id="walkthrough-title"></h2><p id="walkthrough-sentence"></p><div id="walkthrough-progress" aria-hidden="true">'+('<i></i>'.repeat(6))+'</div></div>';
  const cursor=document.createElement('div');cursor.id='walkthrough-cursor';cursor.innerHTML='<svg width="22" height="28" viewBox="0 0 22 28"><path d="M2 1V22L7 17L11 26L15 24L11 16H20Z" fill="#292733" stroke="white" stroke-width="1.5" stroke-linejoin="round"/></svg>';document.body.append(cursor);
 });
 await stage(0,async()=>{await hold(1.8);await go('View Projects');await hold(1.2);await click(page.getByRole('button',{name:/Little Cat Guided Project/}));await hold(1.4);});
 await stage(1,async()=>{await go('Start This Project');await fill(page.getByLabel('Project Name',{exact:true}),'Miso');await hold(1.4);await go('Continue');await hold(2);});
 await stage(2,async()=>{await go('Setup Reviewed');await hold(1.5);await go('Plate Checked');await hold(1.5);await go('Material Checked');await hold(1.8);});
 await stage(3,async()=>{await go('Enter Print Demo');await hold(1);await click(page.getByText('What To Look For',{exact:true}));await hold(1.7);await go('This Layer Looks Good');await hold(1);});
 await stage(4,async()=>{await go('Continue To Demo Finish');await hold(1.5);await go('Removal Reviewed');await hold(.5);await click(page.getByLabel('Object Checked',{exact:false}));await click(page.getByLabel('Workspace Restored',{exact:false}));await hold(.8);await go('Finish My Project');await hold(1.4);});
 await stage(5,async()=>{await fill(page.getByLabel('Add A Note'),'Check the first layer before continuing.');await hold(.6);await go('View Collection');await hold(.7);await click(page.getByRole('button',{name:/Miso Little Cat/}));await hold(.7);});
 await expect(page.getByRole('heading',{name:'Your Project Record',exact:true})).toBeVisible();expect(errors).toEqual([]);
 encoder.stdin.end();const [code]=await finished;if(code!==0)throw Error(encoderError);
 await fs.writeFile(`${out}/storyboard.json`,JSON.stringify({duration:frames/fps,fps,width:1600,height:1000,source:'C:/Users/alexx/Downloads/M4 Value Creation Analysis.pdf',chapters,errors,method:'Isolated browser, real UI actions, capture-only side captions and pointer; held frames edited to 38 seconds. No audio, no simulated print timing.'},null,2)+'\n');
 const time=t=>`00:00:${String(Math.floor(t)).padStart(2,'0')},${String(Math.round(t%1*1000)).padStart(3,'0')}`;
 await fs.writeFile(`${out}/BenchMate-Walkthrough.srt`,chapters.map((c,i)=>`${i+1}\n${time(c.start)} --> ${time(c.end)}\n${c.sentence}\n`).join('\n'));
 await fs.writeFile(`${out}/Walkthrough-Script.txt`,chapters.map(c=>`${c.start}–${c.end}s | ${c.title}\n${c.sentence}\nEvidence: ${c.source}\n`).join('\n')+'\nBenefits are design intentions based on interview accounts, not measured product outcomes. The finishing sentence applies the VCA\'s broader step-guidance need to this prototype. This browser demo does not operate a printer or represent elapsed printing/cooling time.\n');
 console.log(`Saved ${frames} frames / ${frames/fps} seconds.`);
}catch(error){encoder.stdin.destroy();encoder.kill();throw error;}finally{await browser.close();}
