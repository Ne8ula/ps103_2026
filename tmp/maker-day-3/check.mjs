// Screenshot every slide, report anything that spills past the frame, and export the PDF.
// Run from the repo root: node tmp/maker-day-3/check.mjs <screenshot-dir>
import {chromium} from '@playwright/test';
import assert from 'node:assert/strict';
import {pathToFileURL} from 'node:url';
const shots = process.argv[2];
const url = pathToFileURL('BenchMate_Maker_Day_3.html').href;
const browser = await chromium.launch({channel: 'msedge'});
const page = await browser.newPage({viewport: {width: 1636, height: 982}});
const errors = []; page.on('pageerror', e => errors.push(e.message));
await page.goto(url); await page.evaluate(() => document.fonts.ready);
const count = await page.locator('.slide').count();
let spills = 0;
for (let n = 1; n <= count; n++) {
  const report = await page.locator('.slide:visible').evaluate(slide => {
    const frame = slide.querySelector('.frame').getBoundingClientRect();
    const foot = slide.querySelector('.foot').getBoundingClientRect();
    const out = [];
    for (const el of slide.querySelectorAll('.frame *')) {
      if (el.closest('.foot,.cover-art,.cover-wordmark,svg') || el.matches('.cover-baseline')) continue;
      const r = el.getBoundingClientRect();
      if (!r.width || !r.height) continue;
      const clipped = el.matches('h1,h2,h3,p,li,td,th,dd,dt,span') && el.scrollWidth > el.clientWidth + 2;
      if (r.bottom > foot.top + 1 || r.right > frame.right + 1 || r.left < frame.left - 1 || clipped)
        out.push(`${el.tagName}.${el.className} "${el.textContent.trim().slice(0, 40)}" bottom+${Math.round(r.bottom - foot.top)} ${clipped ? 'clipped' : ''}`);
    }
    return {title: slide.dataset.title, free: Math.round(foot.top - Math.max(...[...slide.querySelectorAll('.frame > *:not(.foot):not(.cover-art)')].map(e => e.getBoundingClientRect().bottom))), out};
  });
  spills += report.out.length;
  console.log(n, report.title, '| free px above footer:', report.free, report.out.length ? '\n   ' + report.out.join('\n   ') : '');
  if (shots) await page.screenshot({path: `${shots}/slide-${String(n).padStart(2, '0')}.png`});
  if (n < count) await page.getByRole('button', {name: 'Next slide'}).click();
}
// One slide per page at its native 1600×900, so nothing is shrunk or left with a margin.
await page.addStyleTag({content: '@media print{@page{size:1600px 900px;margin:0}.slide{zoom:1!important}}'});
await page.pdf({path: 'BenchMate_Maker_Day_3.pdf', preferCSSPageSize: true, printBackground: true});
await browser.close();
assert.deepEqual(errors, []);
assert.equal(spills, 0, 'content spills past a slide frame');
