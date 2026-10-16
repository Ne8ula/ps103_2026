import fs from 'node:fs';
import assert from 'node:assert/strict';
const file='BenchMate_Maker_Day_2.html';
let html=fs.readFileSync(file,'utf8');
const learning='<section class="workflow-benefits" aria-labelledby="workflow-benefits-title"><h2 id="workflow-benefits-title">Learning Priorities</h2><ul class="workflow-benefits-list"><li>Visual Guidance</li><li>Contextual Feedback</li><li>Equipment Specificity</li><li>Correctness</li></ul></section>';
assert.ok(html.includes(learning)&&!html.includes('id="organization-priorities-title"'));
html=html.replace(learning,learning+`
<section class="workflow-benefits organization-priorities" aria-labelledby="organization-priorities-title"><h2 id="organization-priorities-title">Organization Priorities</h2><ul class="workflow-benefits-list"><li><strong>Scalability</strong><span>Reuse approved guidance across many learners.</span></li><li><strong>Knowledge Persistence</strong><span>Keep expert know-how beyond one-to-one sessions.</span></li></ul></section>`);
html=html.replace('</style>',`
/* Keep learner and organization priorities together beneath the workflow. */
.workflow-intro {height:150px;}
.workflow-steps {height:310px;}
.workflow-step {padding-top:20px;}
.workflow-illustration {height:145px;}
.workflow-connector {top:137px;}
.workflow-benefits {margin-top:18px;}
.workflow-benefits h2 {margin-bottom:10px;}
.workflow-benefits-list li {padding:14px 12px;}
.organization-priorities {margin-top:18px;}
.organization-priorities .workflow-benefits-list {grid-template-columns:1fr 1fr;background:rgba(214,232,121,.2);}
.organization-priorities li {padding:13px 20px;}
.organization-priorities strong {display:block;font:500 23px/1.3 var(--heading);color:var(--blue);margin-bottom:5px;}
.organization-priorities span {display:block;font:400 16px/1.45 var(--body);letter-spacing:-.3px;color:var(--secondary);}
</style>`);
fs.writeFileSync(file,html);
fs.copyFileSync(file,'sites/benchmate-maker-day-2/dist/index.html');
console.log('Added Organization Priorities below Learning Priorities.');
