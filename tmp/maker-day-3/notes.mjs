// Render the speaker script and the Q&A prep to PDF.
// Run from the repo root: node tmp/maker-day-3/notes.mjs
import {chromium} from '@playwright/test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';

const css = `
@page{size:Letter;margin:.6in .7in}
*{box-sizing:border-box}
body{margin:0;font:10.5pt/1.5 'Segoe UI',Arial,sans-serif;color:#292733}
.kicker{margin:0;font-size:8.5pt;letter-spacing:.12em;text-transform:uppercase;color:#3155D9}
h1{margin:2pt 0 4pt;font-size:24pt;line-height:1.1;letter-spacing:-.02em}
.lede{margin:0 0 10pt;color:#5E6270}
h2{margin:16pt 0 6pt;padding-bottom:3pt;border-bottom:1px solid #D9DBE2;font-size:9pt;letter-spacing:.12em;text-transform:uppercase;color:#3155D9;break-after:avoid}
.key{margin:0 0 10pt;padding:6pt 9pt;background:#F3F4F8;font-size:9.5pt}
.fill{background:#D6E879;padding:0 3pt}
.cut{border-bottom:1.5px dotted #5E6270}
table{width:100%;border-collapse:collapse}
th,td{padding:7pt 8pt;vertical-align:top;text-align:left;border-bottom:1px solid #D9DBE2}
tr{break-inside:avoid}
.script th{font-size:8.5pt;letter-spacing:.1em;text-transform:uppercase;color:#5E6270;border-bottom:1.5px solid #292733}
.script td:nth-child(1){width:44pt;font-weight:600;color:#3155D9;font-variant-numeric:tabular-nums}
.script td:nth-child(2){width:96pt;font-size:9.5pt;color:#5E6270}
.script td:nth-child(2) b{display:block;font-size:13pt;color:#292733}
.say{font-size:11.5pt;line-height:1.55}
.facts th{width:70pt;font-size:9.5pt;color:#3155D9}
.facts td{font-size:9.5pt}
.qa{margin:0 0 9pt;break-inside:avoid}
.qa h3{margin:0 0 2pt;font-size:10.5pt}
.qa p{margin:0}
.notes{break-inside:avoid}
.notes ul{margin:0;padding-left:14pt}
.notes li{margin-bottom:4pt}
`;

const browser = await chromium.launch({channel: 'msedge'});
const page = await browser.newPage();
for (const [name, out] of [['script', 'BenchMate_Maker_Day_3_Script.pdf'], ['qa', 'BenchMate_Maker_Day_3_QA_Prep.pdf']]) {
  const body = readFileSync(`tmp/maker-day-3/notes/${name}.html`, 'utf8');
  await page.setContent(`<!doctype html><meta charset="utf-8"><title>${out}</title><style>${css}</style>${body}`);
  await page.pdf({path: out, preferCSSPageSize: true, printBackground: true});
  const pages = readFileSync(out, 'latin1').match(/\/Type\s*\/Page\b(?!s)/g).length;
  if (name === 'script') {
    const count = sel => page.locator(sel).evaluateAll(els => els.join ? els.map(e => e.textContent).join(' ').trim().split(/\s+/).length : 0);
    const words = await count('.say'), cuts = await count('.say .cut');
    console.log(out, `${pages} pages, ${words} spoken words (${(words / 140).toFixed(2)} min at 140 wpm; ${words - cuts} without the dotted cuts)`);
    assert.ok(words >= 620 && words <= 720, 'script is not about five minutes');
  } else {
    const questions = await page.locator('.qa').count();
    console.log(out, `${pages} pages, ${questions} questions`);
  }
}
await browser.close();
