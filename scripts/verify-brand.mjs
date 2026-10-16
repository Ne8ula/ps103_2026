import {chromium,expect} from '@playwright/test';
import fs from 'node:fs/promises';
const out='docs/evidence/brand-refresh';
const browser=await chromium.launch({headless:true,...(process.env.BENCHMATE_CHROME?{executablePath:process.env.BENCHMATE_CHROME}:{channel:'msedge'}),args:['--enable-unsafe-swiftshader']});
const checks=[];
try {
  for(const [width,height] of [[320,740],[393,852],[430,932],[1440,1000]]) {
    const context=await browser.newContext({viewport:{width,height},deviceScaleFactor:1});
    const page=await context.newPage();
    const failures=[];
    page.on('pageerror',e=>failures.push(e.message));
    page.on('response',r=>{if(r.status()>=400)failures.push(`${r.status()} ${r.url()}`);});
    await page.goto(process.env.BENCHMATE_URL||'http://127.0.0.1:4174');
    await page.evaluate(()=>Promise.all(['500 16px "Space Grotesk"','700 16px "Space Grotesk"','400 16px "Space Mono"','700 16px "Space Mono"','400 16px "Silkscreen"'].map(font=>document.fonts.load(font))));
    await page.evaluate(()=>document.fonts.ready);
    await page.waitForFunction(()=>document.querySelector('[data-renderer]')?.dataset.renderer==='ready');
    const result=await page.evaluate(()=>{
      const style=s=>getComputedStyle(document.querySelector(s));
      return {heading:style('h1').fontFamily,body:style('body').fontFamily,technical:style('.scene-caption').fontFamily,action:style('.primary').backgroundColor,
        fonts:[['Space Grotesk',500],['Space Grotesk',700],['Space Mono',400],['Space Mono',700],['Silkscreen',400]].map(([family,weight])=>({family,weight,loaded:document.fonts.check(`${weight} 16px "${family}"`)})),
        images:[...document.querySelectorAll('.brand-wordmark,.brand-logo')].map(img=>({src:img.getAttribute('src'),loaded:img.complete&&img.naturalWidth>0})),
        overflow:document.documentElement.scrollWidth>innerWidth};
    });
    expect(result.heading).toContain('Space Grotesk');expect(result.body).toContain('Space Mono');expect(result.technical).toContain('Silkscreen');
    expect(result.action).toBe('rgb(49, 85, 217)');expect(result.fonts.every(f=>f.loaded)).toBe(true);expect(result.images.every(i=>i.loaded)).toBe(true);expect(result.overflow).toBe(false);
    await page.screenshot({path:`${out}/showcase-home-${width}.png`,animations:'disabled'});
    if(width===320) {
      await page.getByRole('button',{name:'View Projects',exact:true}).click();
      await page.getByRole('button',{name:/Little Cat Guided Project/}).click();
      await page.getByRole('button',{name:'Start This Project',exact:true}).click();
      await page.getByRole('button',{name:'Continue',exact:true}).click();
      await page.getByRole('button',{name:'Setup Reviewed',exact:true}).click();
      await page.getByText('Plate Details',{exact:true}).click();
      await page.locator('.disclosure').scrollIntoViewIfNeeded();
      // Detect clipped text inside scroll containers, not just document overflow.
      const clipped=await page.locator('p,button,dt,dd,summary,.phase-rail li>span:nth-child(2)').evaluateAll(nodes=>nodes.filter(e=>e.clientWidth&&e.scrollWidth>e.clientWidth+2).map(e=>e.textContent));
      expect(clipped).toEqual([]);
      await page.screenshot({path:`${out}/guidance-320.png`,animations:'disabled'});
      await page.getByRole('button',{name:'Help',exact:true}).click();
      expect(await page.getByRole('dialog').evaluate(el=>Math.round(el.getBoundingClientRect().width))).toBe(width);
      await page.screenshot({path:`${out}/help-320.png`,animations:'disabled'});
      await page.keyboard.press('Escape');
      await expect(page.getByRole('button',{name:'Help',exact:true})).toBeFocused();
    }
    expect(failures).toEqual([]);checks.push({width,height,...result,failures});
    await context.close();
  }
  await fs.writeFile(`${out}/brand-verification.json`,JSON.stringify({date:'2026-10-16',checks},null,2)+'\n');
  console.log('Brand fonts, assets, action color, narrow guidance and four showcase sizes passed.');
} finally {await browser.close();}

