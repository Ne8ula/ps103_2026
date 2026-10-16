import fs from 'node:fs';
import assert from 'node:assert/strict';
const p='BenchMate_Maker_Day_2.html';
let h=fs.readFileSync(p,'utf8');
assert.ok(h.includes('Saved Per Resolved Shift'));
h=h.replace('Saved Per Resolved Shift','Saved Per Support Contact');
h=h.replace('<p class="roi-benchmark-detail">$13.50 assisted → $1.84 self-service</p>', '<p class="roi-benchmark-detail">$13.50 assisted − $1.84 self-service</p><p class="roi-unit-explanation">Savings when one support request is resolved through self-service instead of staff help.</p>');
h=h.replace('<dt>Fully Resolved Shift</dt>','<dt>Support Shifted To Self-Service</dt>');
h=h.replace('<div><dt>Onboarding Labor / Hour</dt><dd>$40</dd></div>','<div><dt>Onboarding Labor / Hour</dt><dd>$40</dd><p class="roi-hour-explanation">Staff cost per hour saved on setup &amp; training.</p></div>');
const label='<text x="176.850" y="65" class="roi-bar-value">+$2,988</text>';
assert.ok(h.includes(label));
h=h.replace(label,label+'<text x="365" y="41" class="roi-support-explanation"><tspan x="365" dy="0">1,800 requests shift to self-service:</tspan><tspan x="365" dy="22">$20,988 saved − $18,000 license</tspan><tspan x="365" dy="22">leaves $2,988, before onboarding.</tspan></text>');
h=h.replace('</style>',`
/* Explain support savings per contact versus onboarding labor per hour. */
.manufacturer-roi .roi-intro {height:150px;}
.manufacturer-roi .roi-content {height:430px;}
.manufacturer-roi .roi-section-heading {margin-bottom:16px;}
.manufacturer-roi .roi-benchmark-detail {margin-bottom:9px;}
.roi-unit-explanation {font:400 15px/1.5 var(--body);letter-spacing:-.3px;margin:0 0 17px;color:var(--secondary);max-width:455px;}
.manufacturer-roi .roi-assumption-grid {gap:18px 20px;padding-top:15px;}
.roi-hour-explanation {order:2;font:400 13px/1.45 var(--body);letter-spacing:-.2px;color:var(--secondary);margin:0;}
.roi-support-explanation {font:400 15px var(--body);fill:var(--secondary);letter-spacing:-.25px;}
</style>`);
fs.writeFileSync(p,h);fs.copyFileSync(p,'sites/benchmate-maker-day-2/dist/index.html');
assert.equal(6000*.3*11.66-18000,2988);
console.log('Clarified both units and support-only net savings.');
