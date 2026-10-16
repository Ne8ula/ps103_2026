import fs from 'node:fs';
import assert from 'node:assert/strict';
const file='BenchMate_Maker_Day_2.html';
let html=fs.readFileSync(file,'utf8');
assert.ok(!html.includes('id="slide-financial-feasibility"'));
const start=html.indexOf('<article class="slide feasibility"');
const end=html.indexOf('</article>',start)+10;
const original=html.slice(start,end);
const header=original.match(/<header[\s\S]*?<\/header>/)[0];
const columns=original.match(/<section class="feasibility-column">[\s\S]*?<\/section>/g);
const model=original.match(/<section class="feasibility-model"[\s\S]*?<\/section>/)[0];
const profit=original.match(/<table class="feasibility-profit">[\s\S]*?<\/table>/)[0];
const technical=`<article class="slide feasibility delivery-feasibility" hidden id="slide-feasibility" data-title="Technical &amp; Operational Feasibility" aria-labelledby="feasibility-title"><div class="frame">
${header}
<section class="feasibility-intro"><h1 id="feasibility-title">Can We Make It?</h1><p>Technical &amp; Operational Feasibility</p></section>
<div class="feasibility-columns">${columns.slice(0,2).join('\n')}</div>
<section class="feasibility-stack" aria-labelledby="feasibility-stack-title"><h2 id="feasibility-stack-title">Proposed Tech Stack</h2><div class="stack-parts">
<div><h3>MediaPipe Hands</h3><p>Hand Tracking</p></div>
<div><h3>GestLLM</h3><p>Gesture Interpretation</p></div>
<div><h3>GPT-5.4 Mini</h3><p>Guide &amp; Feedback Drafting</p></div>
<div><h3>RAG</h3><p>Source-Linked Retrieval</p></div>
</div></section>
<p class="feasibility-source">Sources: BenchMate Value Creation, p. 2 · <a href="https://arxiv.org/abs/2501.07295" target="_blank" rel="noopener noreferrer">GestLLM Research</a></p>
<footer class="foot"><span>BENCHMATE / FEASIBILITY</span><span>10 / CAN WE MAKE IT?</span></footer>
</div></article>`;
const financial=`<article class="slide feasibility financial-feasibility" hidden id="slide-financial-feasibility" data-title="Financial Feasibility" aria-labelledby="financial-feasibility-title"><div class="frame">
${header}
<section class="feasibility-intro"><h1 id="financial-feasibility-title">Financial Feasibility</h1><p>Profitability Needs Scale</p></section>
<dl class="finance-metrics">
<div><dt>Annual License</dt><dd>$18K</dd></div>
<div><dt>Variable Cost / License / Year</dt><dd>$6K</dd></div>
<div class="finance-contribution"><dt>Contribution / License / Year</dt><dd>$12K</dd></div>
<div><dt>Annual Fixed Costs</dt><dd>$210K</dd></div>
</dl>
<div class="finance-body"><section class="finance-cost"><h2>What Does $6K Cover?</h2><p class="finance-cost-intro">A delivery allowance per license:<br><strong>$500 / Month</strong> on average.</p>
<ul><li><strong>Content</strong><span>Expert review &amp; guide updates</span></li><li><strong>Service</strong><span>Customer support &amp; maintenance</span></li><li><strong>Usage</strong><span>Cloud hosting &amp; AI/API calls</span></li></ul>
<p class="finance-cost-note">Planning Allowance · Allocation To Validate</p></section>
<section class="finance-scale" aria-label="Modeled profitability">${profit}<p class="feasibility-break-even">Break-Even: <strong>18 Active Licenses</strong></p><p class="feasibility-assumption-note">Assumptions, Not Sales Forecasts</p></section></div>
${model}
<p class="feasibility-source">Source: BenchMate Value Creation, p. 2 · $6K categories clarify the assumption; no itemized allocation is provided in the PDF.</p>
<footer class="foot"><span>BENCHMATE / FEASIBILITY</span><span>11 / FINANCIAL FEASIBILITY</span></footer>
</div></article>`;
html=html.slice(0,start)+technical+'\n\n'+financial+html.slice(end);
html=html.replace('11 / CENTRAL BUSINESS LOGIC','12 / CENTRAL BUSINESS LOGIC').replace('12 / VALIDATION TO COMMERCIAL USE','13 / VALIDATION TO COMMERCIAL USE').replace('13 / THANK YOU','14 / THANK YOU').replace('Introduction / 1 of 13','Introduction / 1 of 14');
const css=`
/* Technical delivery and financial feasibility each get a full slide. */
.delivery-feasibility .feasibility-intro {height:158px;}
.delivery-feasibility .feasibility-columns {grid-template-columns:1fr 1fr;height:330px;gap:58px;}
.delivery-feasibility .feasibility-column {border-top:2px solid var(--blue);padding-top:21px;}
.delivery-feasibility .feasibility-column + .feasibility-column {padding-left:42px;}
.delivery-feasibility .feasibility-label {margin-bottom:14px;}
.delivery-feasibility .feasibility-column h2 {font-size:36px;margin-bottom:24px;min-height:0;}
.delivery-feasibility .feasibility-detail {margin-bottom:22px;}
.delivery-feasibility .feasibility-detail h3 {font-size:25px;margin-bottom:7px;}
.delivery-feasibility .feasibility-detail p {font-size:20px;max-width:600px;}
.feasibility-stack {margin:20px 42px 0;padding:23px 27px 27px;background:var(--cloud);border-top:1px solid var(--rule);}
.feasibility-stack > h2 {font:400 16px/1.4 var(--technical);color:var(--blue);margin:0 0 24px;}
.stack-parts {display:grid;grid-template-columns:repeat(4,1fr);gap:25px;}
.stack-parts > div + div {border-left:1px solid var(--rule);padding-left:25px;}
.stack-parts h3 {font:500 26px/1.2 var(--heading);letter-spacing:-.7px;margin:0 0 9px;}
.stack-parts p {font:400 15px/1.5 var(--body);margin:0;color:var(--secondary);}
.stack-parts > div:nth-child(2) h3 {display:table;background:var(--lime);padding:0 6px;margin-left:-6px;}
.delivery-feasibility .feasibility-source,.financial-feasibility .feasibility-source {position:absolute;bottom:51px;left:42px;margin:0;}
.feasibility-source a {color:inherit;text-underline-offset:3px;}
.financial-feasibility .feasibility-intro {height:148px;}
.finance-metrics {display:grid;grid-template-columns:repeat(4,1fr);gap:26px;margin:0 42px;height:115px;}
.finance-metrics > div {border-top:2px solid var(--blue);padding:13px 15px;display:flex;flex-direction:column;gap:6px;}
.finance-metrics dd {font:500 46px/1.1 var(--heading);letter-spacing:-1.7px;color:var(--blue);margin:0;}
.finance-metrics dt {order:1;font:400 14px/1.4 var(--body);color:var(--secondary);}
.finance-contribution {background:var(--lime);}
.finance-body {display:grid;grid-template-columns:1fr 1fr;gap:65px;margin:24px 42px 0;height:290px;}
.finance-cost h2 {font:500 29px/1.2 var(--heading);letter-spacing:-.7px;margin:0 0 10px;}
.finance-cost-intro {font:400 18px/1.4 var(--body);margin:0 0 15px;}
.finance-cost-intro br {display:none;}
.finance-cost-intro strong {color:var(--blue);font-weight:500;}
.finance-cost ul {padding:0;margin:0;list-style:none;}
.finance-cost li {display:grid;grid-template-columns:115px 1fr;gap:12px;border-top:1px solid var(--rule);padding:9px 0;font:400 17px/1.4 var(--body);}
.finance-cost li strong {font-weight:500;color:var(--blue);}
.finance-cost-note {font:400 12px/1.4 var(--body);color:var(--secondary);margin:10px 0 0;}
.finance-scale {padding-left:40px;border-left:1px solid var(--rule);}
.finance-scale .feasibility-profit caption {font-size:16px;margin-bottom:17px;}
.finance-scale .feasibility-profit th {font-size:16px;}
.finance-scale .feasibility-profit td {font-size:32px;padding:15px 0;}
.finance-scale .feasibility-break-even {font-size:25px;margin-top:21px;}
.financial-feasibility .feasibility-model {margin-top:10px;min-height:95px;padding:15px 26px;}
.financial-feasibility .feasibility-equations {font-size:20px;}
`;
html=html.replace('</style>',css+'\n</style>');
assert.equal((html.match(/<article class="slide /g)||[]).length,14);
fs.writeFileSync(file,html);
fs.copyFileSync(file,'sites/benchmate-maker-day-2/dist/index.html');
console.log('Split feasibility: 14 slides; financial model retained.');
