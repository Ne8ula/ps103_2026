import fs from 'node:fs';
import assert from 'node:assert/strict';
const p='BenchMate_Maker_Day_2.html';
let h=fs.readFileSync(p,'utf8');
const changes=[
 ['<p class="technical-stack">MediaPipe Hands + GPT-5.4 Mini + RAG</p>','<p class="technical-stack">MediaPipe Hands + GestLLM + GPT-5.4 Mini + RAG</p>'],
 ['.stack-parts > div:nth-child(2) h3 {display:table;background:var(--lime);padding:0 6px;margin-left:-6px;}',''],
 ['<div><dt>Annual License</dt><dd>$18K</dd></div>','<div class="finance-highlight"><dt>Annual License</dt><dd>$18K</dd></div>'],
 ['<div class="finance-contribution"><dt>Contribution / License / Year</dt>','<div><dt>Contribution / License / Year</dt>'],
 ['.finance-contribution {background:var(--lime);}', '.finance-highlight {background:var(--lime);}']
];
for(const [before,after] of changes){assert.ok(h.includes(before),before);h=h.replace(before,after);}
fs.writeFileSync(p,h);fs.copyFileSync(p,'sites/benchmate-maker-day-2/dist/index.html');
console.log('Updated slide 4 stack and slides 10–11 highlights.');
