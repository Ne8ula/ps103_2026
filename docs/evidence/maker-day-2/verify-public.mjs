import { chromium } from '@playwright/test';
import assert from 'node:assert/strict';
import fs from 'node:fs';

const url = 'https://benchmate-maker-day-2.sunsetreed.chatgpt.site';
const browser = await chromium.launch({ channel: 'msedge' });
try {
  const context = await browser.newContext({ viewport: { width: 1600, height: 1000 } });
  const results = { url, anonymous: true, videos: [] };
  for (const [slide, id] of [[8, 'mockup-video'], [9, 'walkthrough-video']]) {
    const page = await context.newPage();
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    const response = await page.goto(`${url}/#${slide}`, { waitUntil: 'load', timeout: 60000 });
    assert.equal(response.status(), 200);
    assert.equal(await page.locator('.slide').count(), 14);
    await page.waitForFunction(id => {
      const video = document.getElementById(id);
      return video && video.currentTime > 0.2 && !video.paused && video.readyState >= 2;
    }, id, { timeout: 30000 });
    const video = await page.locator(`#${id}`).evaluate(v => ({
      duration: v.duration, width: v.videoWidth, height: v.videoHeight,
      currentTime: v.currentTime, playing: !v.paused, error: v.error?.message ?? null,
      controls: v.controls
    }));
    assert.ok(video.width > 0 && video.height > 0 && video.duration > 0);
    assert.equal(video.error, null);
    await page.locator(`#${id}`).evaluate(v => { v.pause(); v.currentTime = Math.min(8, v.duration / 2); });
    await page.waitForFunction(id => !document.getElementById(id).seeking, id);
    await page.screenshot({ path: `docs/evidence/maker-day-2/public-slide-${slide}.png` });
    await page.locator(`#${id}`).evaluate(v => v.play());
    assert.equal(await page.locator(`#${id}`).evaluate(v => v.paused), false);
    assert.deepEqual(errors, []);
    results.videos.push({ slide, id, ...video, seekAndResume: true, errors });
    await page.close();
  }
  fs.writeFileSync('docs/evidence/maker-day-2/public-checks.json', JSON.stringify(results, null, 2));
  console.log(JSON.stringify(results, null, 2));
} finally {
  await browser.close();
}
