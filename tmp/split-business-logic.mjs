import fs from 'node:fs';
import assert from 'node:assert/strict';
const file = 'BenchMate_Maker_Day_2.html';
let html = fs.readFileSync(file, 'utf8');
const start = html.indexOf('<article class="slide business-logic"');
const end = html.indexOf('</article>', start) + '</article>'.length;
const original = html.slice(start, end);
assert.ok(start > 0 && !html.includes('id="slide-market-path"'));
const header = original.match(/<header[\s\S]*?<\/header>/)[0];
const flow = original.match(/<section class="logic-wedge-flow"[\s\S]*?(?=<p class="logic-source">)/)[0];
const source = original.match(/<p class="logic-source">[\s\S]*?<\/p>/)[0];
const icon = paths => `<div class="logic-condition-icon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${paths}</svg></div>`;
const icons = [
  icon('<path d="M3 17 9 11l4 4 8-10M15 5h6v6"/><path d="M3 3v18h18"/>'),
  icon('<path d="M12 3 3 7v6c0 5 9 8 9 8s9-3 9-8V7Z"/><path d="m8 12 3 3 5-6"/>'),
  icon('<rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><path d="M14 17.5h7m-3.5-3.5v7"/>')
];
let first = original.replace(flow, '');
let index=0;
first = first.replace(/(<p class="logic-condition-label">[\s\S]*?<\/p>)/g, m => m+icons[index++]);
first = first.replace(source, '<div class="logic-principle"><span>The Business Logic</span><p>Deliver Buyer Value. Keep Guidance Trusted. Make It Repeatable.</p></div>'+source);
const second = `<article class="slide business-logic market-path" hidden id="slide-market-path" data-title="From Validation To Commercial Use" aria-labelledby="market-path-title"><div class="frame">
${header}
<section class="logic-intro"><h1 id="market-path-title">From Validation To Commercial Use</h1><p>Start with one focused task. Expand to a manufacturer-backed use case.</p></section>
${flow}
${source}
<footer class="foot"><span>BENCHMATE / MARKET PATH</span><span>12 / VALIDATION TO COMMERCIAL USE</span></footer>
</div></article>`;
html = html.slice(0,start)+first+'\n\n'+second+html.slice(end);
html = html.replace('12 / THANK YOU', '13 / THANK YOU').replace('Introduction / 1 of 12','Introduction / 1 of 13');
const css = `
/* Separate business conditions and market path into two spacious slides. */
.business-logic .logic-intro {height:164px;}
.business-logic .logic-conditions {height:398px;gap:30px;}
.business-logic .logic-condition {padding:22px 0 0;border-top:2px solid var(--blue);}
.business-logic .logic-condition + .logic-condition {border-left:0;padding-left:28px;border-left:1px solid var(--rule);}
.business-logic .logic-condition-label {font-size:18px;margin-bottom:28px;}
.logic-condition-icon {height:92px;display:flex;align-items:center;color:var(--blue);margin-bottom:26px;}
.logic-condition-icon svg {width:66px;height:66px;}
.logic-condition:last-child .logic-condition-icon svg {background:var(--lime);border-radius:12px;padding:13px;box-sizing:content-box;width:54px;height:54px;}
.business-logic .logic-condition h2 {font-size:32px;min-height:77px;margin-bottom:18px;}
.business-logic .logic-condition > p:last-child {font-size:20px;line-height:1.5;max-width:410px;}
.logic-principle {margin:24px 42px 0;padding:22px 26px;background:var(--blue);color:white;display:flex;align-items:center;gap:36px;}
.logic-principle span {font:400 14px/1.5 var(--technical);color:var(--lime);white-space:nowrap;}
.logic-principle p {font:500 26px/1.4 var(--heading);letter-spacing:-.6px;margin:0;}
.business-logic .logic-source {position:absolute;left:42px;bottom:53px;margin:0;}
.market-path .logic-wedge-flow {height:460px;margin:4px 42px 0;padding-top:24px;grid-template-columns:minmax(0,1fr) 150px minmax(0,1fr);border-top:0;}
.market-path .logic-wedge {padding:23px 24px 30px;border-top:2px solid var(--blue);}
.market-path .logic-wedge-commercial {background:rgba(214,232,121,.18);}
.market-path .logic-wedge-label {font:500 26px/1.3 var(--heading);letter-spacing:-.6px;margin-bottom:28px;}
.market-path .logic-wedge-icon {height:148px;}
.market-path .logic-wedge-icon svg {width:116px;height:116px;}
.market-path .logic-wedge-commercial .logic-wedge-icon svg {width:100px;height:100px;padding:19px;border-radius:18px;}
.market-path .logic-wedge h3 {font-size:34px;margin:30px 0 17px;}
.market-path .logic-wedge-description {font-size:22px;line-height:1.6;}
.market-path .logic-wedge-arrow {height:148px;margin-top:85px;}
`;
html = html.replace('</style>', css+'\n</style>');
assert.equal((html.match(/<article class="slide /g)||[]).length,13);
fs.writeFileSync(file,html);
fs.copyFileSync(file,'sites/benchmate-maker-day-2/dist/index.html');
console.log('Updated local presentation and publishing copy: 13 slides.');
