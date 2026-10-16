import fs from 'node:fs';
import assert from 'node:assert/strict';
const file='BenchMate_Maker_Day_2.html';
let html=fs.readFileSync(file,'utf8');
const start=html.indexOf('<article class="slide differentiation"');
const end=html.indexOf('</article>',start)+10;
const original=html.slice(start,end);
const technical=original.match(/<section class="technical-basis"[\s\S]*?<\/section>/)[0];
let slide=original;
const replacements=[
 ['BenchMate targets <strong>novice learners</strong> using specific lab equipment.','Built for <strong>novice learners</strong> on their exact machine.'],
 ['Existing solutions','Existing Solutions'],
 ['AI-assisted expert videos for industrial training','AI training videos'],
 ['Manuals, SOPs and video converted into guided procedures','Guided procedures'],
 ['BenchMate’s proposed differentiation','BenchMate’s Focus'],
 ['Machine-specific','Machine-Specific'],
 ['Expert-reviewed','Expert-Reviewed'],
 ['Novice-first','Novice-First'],
 ['Exact equipment model, task and local procedures','Your model. Your task.'],
 ['Manuals, SOPs and expert demos reviewed by instructors','Approved by instructors.'],
 ['Visual steps, feedback and instructor handoff','Visual steps + feedback.']
];
for(const [before,after] of replacements){assert.ok(slide.includes(before));slide=slide.replace(before,after);}
slide=slide.replace(/<span class="pillar-number">\d+<\/span>/g,'');
assert.equal(slide.match(/<section class="technical-basis"[\s\S]*?<\/section>/)[0],technical);
html=html.slice(0,start)+slide+html.slice(end);
html=html.replace('</style>',`
/* A faster read: brief competitor context and three concise focus areas. */
.differentiation .comparison-body {grid-template-columns:310px minmax(0,1fr);gap:46px;}
.differentiation .existing-solutions {padding-right:30px;}
.differentiation .competitor {padding-top:35px;}
.differentiation .competitor + .competitor {padding-top:42px;}
.differentiation .pillar-top {height:156px;}
.differentiation .difference-pillar h3 {font-size:33px;margin-bottom:14px;}
.differentiation .difference-pillar p {font-size:21px;color:var(--secondary);}
</style>`);
fs.writeFileSync(file,html);fs.copyFileSync(file,'sites/benchmate-maker-day-2/dist/index.html');
console.log('Simplified slide 6; Technical Basis preserved byte-for-byte.');
