import fs from 'node:fs';
import assert from 'node:assert/strict';
const file='BenchMate_Maker_Day_2.html';
let html=fs.readFileSync(file,'utf8');
const start=html.indexOf('<article class="slide differentiation"');
const end=html.indexOf('</article>',start)+10;
const original=html.slice(start,end);
const technical=original.match(/<section class="technical-basis"[\s\S]*?<\/section>/)[0];
let slide=original;
slide=slide.replace('<section class="competitor"><h3>DeepHow</h3><p>AI training videos</p></section>','<section class="competitor"><h3><a href="https://deephow.com/" target="_blank" rel="noopener noreferrer">DeepHow</a></h3><p>AI-assisted video training for workers</p></section>');
const taqtile='<section class="competitor"><h3>Taqtile</h3><p>Guided procedures</p></section>';
assert.ok(slide.includes(taqtile));
slide=slide.replace(taqtile,'<section class="competitor"><h3><a href="https://www.taqtile.com/create/" target="_blank" rel="noopener noreferrer">Taqtile</a></h3><p>AR-guided work instructions for teams</p></section>\n<section class="competitor"><h3><a href="https://bilt.ai/" target="_blank" rel="noopener noreferrer">BILT</a></h3><p>Interactive 3D product assembly instructions</p></section>');
let n=0;slide=slide.replace(/<div class="pillar-top">/g,m=>m+`<span class="pillar-number">${String(++n).padStart(2,'0')}</span>`);
assert.equal(n,3);
assert.equal(slide.match(/<section class="technical-basis"[\s\S]*?<\/section>/)[0],technical);
html=html.slice(0,start)+slide+html.slice(end);
html=html.replace('</style>',`
/* Three concise competitor entries, with the original numbered accents. */
.differentiation .competitor,.differentiation .competitor + .competitor {padding-top:22px;}
.differentiation .competitor h3 {font-size:29px;margin-bottom:7px;}
.differentiation .competitor p {font-size:18px;line-height:1.4;letter-spacing:-.4px;}
.differentiation .competitor a {color:inherit;text-decoration:none;}
.differentiation .competitor a:focus-visible {outline:2px solid var(--blue);outline-offset:4px;}
</style>`);
fs.writeFileSync(file,html);fs.copyFileSync(file,'sites/benchmate-maker-day-2/dist/index.html');
console.log('Restored 01–03; added BILT; each competitor has a five-word description. Technical Basis unchanged.');
