import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {chromium} from '@playwright/test';

const dir=path.dirname(fileURLToPath(import.meta.url));
await fs.mkdir(dir,{recursive:true});
// u = 8. Every straight-segment endpoint, circle centre and radius is on this grid.
const d='M64 48H136A8 8 0 0 1 144 56V88H96A8 8 0 0 0 88 96V104A8 8 0 0 0 96 112H112V144A8 8 0 0 1 104 152H48V64A16 16 0 0 1 64 48Z';
const geometry=`<path d="${d}"/><path d="${d}" transform="rotate(180 128 128)"/>`;
const svg=(color,viewBox='0 0 256 256')=>`<svg xmlns="http://www.w3.org/2000/svg" width="1024" height="1024" viewBox="${viewBox}" role="img" aria-labelledby="title desc"><title id="title">BenchMate — Soft Joint</title><desc id="desc">Two complementary shapes related by an exact 180-degree rotation. Constructed on an 8-unit grid with circular corner radii of 8 and 16 units.</desc><g fill="${color}">${geometry}</g></svg>`;
for(const [name,color] of [['blue','#3155D9'],['black','#000000'],['white','#FFFFFF']]){
 await fs.writeFile(path.join(dir,`benchmate-soft-joint-${name}.svg`),svg(color));
}
await fs.writeFile(path.join(dir,'benchmate-soft-joint-tight.svg'),svg('#3155D9','48 48 160 160'));

const anchors=[[64,48],[136,48],[144,56],[144,88],[96,88],[88,96],[88,104],[96,112],[112,112],[112,144],[104,152],[48,152],[48,64]];
const circles=[[64,64,16],[136,56,8],[96,96,8],[96,104,8],[104,144,8]];
const guides=anchors.map(([x,y])=>`<circle cx="${x}" cy="${y}" r=".9" fill="#D6E879" stroke="#182C7A" stroke-width=".3"/>`).join('');
const guideCircles=circles.map(([x,y,r])=>`<circle cx="${x}" cy="${y}" r="${r}"/><path d="M${x-2} ${y}h4M${x} ${y-2}v4"/>`).join('');
const proof=`<svg xmlns="http://www.w3.org/2000/svg" width="1600" height="1000" viewBox="0 0 1600 1000">
<title>BenchMate Soft Joint — geometric construction</title><desc>Construction grid, exact circular radii, bounds, symmetry, clear-space specification and small-size previews.</desc>
<defs><pattern id="grid" width="8" height="8" patternUnits="userSpaceOnUse"><path d="M8 0H0V8" fill="none" stroke="#3155D9" stroke-opacity=".14" stroke-width=".25"/></pattern><pattern id="major" width="40" height="40" patternUnits="userSpaceOnUse"><path d="M40 0H0V40" fill="none" stroke="#3155D9" stroke-opacity=".22" stroke-width=".4"/></pattern></defs>
<rect width="1600" height="1000" fill="#FCFCFE"/>
<g fill="#292733" font-family="Arial,sans-serif"><text x="64" y="58" font-size="14" letter-spacing="2" fill="#3155D9">BENCHMATE / SOFT JOINT / VECTOR MASTER 1.0</text><text x="64" y="112" font-size="40" font-weight="600">A precise grid. Two complementary parts.</text><path d="M64 143H1536" stroke="#D9DBE2"/>
<g transform="translate(64 180) scale(2.6)">
<rect width="256" height="256" fill="url(#grid)"/><rect width="256" height="256" fill="url(#major)"/>
<rect x="16" y="16" width="224" height="224" fill="none" stroke="#83983E" stroke-width=".65" stroke-dasharray="3 2"/>
<rect x="48" y="48" width="160" height="160" fill="none" stroke="#3155D9" stroke-width=".55"/>
<g stroke="#3155D9" stroke-width=".4" stroke-dasharray="2 2" opacity=".55"><path d="M128 0V256M0 128H256"/></g>
<g fill="#3155D9">${geometry}</g>
<g fill="none" stroke="#E17753" stroke-width=".5" stroke-dasharray="1.2 1">${guideCircles}<g transform="rotate(180 128 128)">${guideCircles}</g></g>
${guides}<g transform="rotate(180 128 128)">${guides}</g>
<g stroke="#3155D9" stroke-width=".55" fill="none"><path d="M48 38V32M208 38V32M48 35H208M48 35l3 -1.5m-3 1.5l3 1.5M208 35l-3 -1.5m3 1.5l-3 1.5"/><circle cx="128" cy="128" r="2"/><path d="M123 128h10M128 123v10"/></g>
<g font-family="monospace" font-size="4.6" fill="#3155D9"><text x="128" y="29" text-anchor="middle">20u / 160 units</text><text x="128" y="220" text-anchor="middle">180° about (128, 128)</text><text x="128" y="249" text-anchor="middle" fill="#5E6927">Dashed boundary = minimum clear space</text></g>
</g>
<text x="64" y="892" font-size="14" fill="#5E6270">Grid intersections govern endpoints and circle centres.</text><text x="64" y="916" font-size="14" fill="#5E6270">Curves between those points are true circular arcs.</text>
<g transform="translate(840 193)"><text font-size="14" fill="#3155D9" letter-spacing="1">CONSTRUCTION SPECIFICATION</text>
<g font-size="22"><text y="49">Base module</text><text x="480" y="49" text-anchor="end">u = 8 units</text><text y="99">Visible mark</text><text x="480" y="99" text-anchor="end">20u × 20u</text><text y="149">Small / large radii</text><text x="480" y="149" text-anchor="end">1u / 2u</text><text y="199">Rotational symmetry</text><text x="480" y="199" text-anchor="end">180°</text><text y="249">Minimum clear space</text><text x="480" y="249" text-anchor="end">4u each side</text><text y="299">Master artboard</text><text x="480" y="299" text-anchor="end">32u × 32u</text></g>
<g stroke="#D9DBE2"><path d="M0 66H600M0 116H600M0 166H600M0 216H600M0 266H600M0 316H600"/></g>
<g font-size="16" fill="#5E6270"><text y="353">Equal 6u margins in the master SVG.</text><text y="380">Use at least 4u around the visible mark in layouts.</text><text y="407">The tight SVG needs clear space added by the layout.</text></g>
<text y="458" font-size="14" fill="#3155D9" letter-spacing="1">COLOUR + SMALL-SIZE CHECK</text><rect y="477" width="28" height="28" fill="#3155D9"/><text x="42" y="498" font-size="18">Electric Blue · #3155D9</text>
<g transform="translate(0 530)" fill="#3155D9"><svg width="24" height="24" viewBox="48 48 160 160">${geometry}</svg><svg x="100" width="32" height="32" viewBox="48 48 160 160">${geometry}</svg><svg x="215" width="48" height="48" viewBox="48 48 160 160">${geometry}</svg><svg x="350" width="64" height="64" viewBox="48 48 160 160">${geometry}</svg></g>
<g font-family="monospace" font-size="13" fill="#5E6270"><text y="625">24 px</text><text x="100" y="625">32 px</text><text x="215" y="625">48 px</text><text x="350" y="625">64 px</text></g>
<text y="674" font-size="16" fill="#5E6270">Recommended minimum: 24 px visible-mark width.</text><text y="701" font-size="16" fill="#5E6270">The construction grid is not part of the logo artwork.</text>
</g><path d="M64 949H1536" stroke="#D9DBE2"/><text x="64" y="978" font-family="monospace" font-size="12" fill="#5E6270">ROUND 02 / CONCEPT 03 REFINED — ORIGINAL SILHOUETTE, EXACT CIRCULAR CORNERS</text></g></svg>`;
await fs.writeFile(path.join(dir,'benchmate-soft-joint-construction.svg'),proof);
await fs.writeFile(path.join(dir,'README.txt'),`BENCHMATE / SOFT JOINT / VECTOR MASTER 1.0

Selected concept: round 02, concept 03 (Soft Joint).
Refinement: retain the silhouette; replace quadratic corner approximations with tangent circular arcs. The second piece is an exact 180-degree copy of the first.

FILES
benchmate-soft-joint-blue.svg   Main transparent vector, Electric Blue #3155D9.
benchmate-soft-joint-black.svg  One-colour black vector.
benchmate-soft-joint-white.svg  One-colour white vector for dark backgrounds.
benchmate-soft-joint-tight.svg  Blue vector with the viewBox cropped to visible artwork; add clear space in the layout.
benchmate-soft-joint-construction.svg  Separate vector construction sheet, not logo artwork.
benchmate-soft-joint-preview.png  Raster preview only.
benchmate-soft-joint-construction.png  Raster preview of the construction sheet.
geometry-checks.json  Measured geometry and raster symmetry check.

GEOMETRY
Base module u = 8 units.
Visible bounds: x=48, y=48, width=160, height=160 (20u square).
Master artboard: 256 x 256 units (32u square).
Artboard margins: 48 units (6u) on every side.
Small circular radii: 8 units (1u). Large outer circular radii: 16 units (2u).
Centre: (128,128). Symmetry: exactly 180 degrees.
All line/arc endpoints and circle centres are multiples of 8 units.
Curved outlines naturally travel between grid points.

USAGE
Keep at least 32 units (4u, 20% of visible-mark width) clear on all sides. This is the proposed clear-space rule for this mark.
Recommended minimum visible-mark width: 24 px. The padded master needs 38.4 px overall to show a 24 px mark. Use the tight SVG with external clear space for precise small-size layout.
Maintain aspect ratio. Do not alter the gap, radius ratio or relative positions of the two pieces.
The grid and clear-space specifications are design rules for this logo, not a claim of a universal logo-grid standard.
No font, linked image, raster content or external dependency is needed by the standalone logo SVGs.
The logo SVGs contain filled paths; there are no strokes to expand.
`);

const browser=await chromium.launch({headless:true,channel:'chrome'});
try {
 const page=await browser.newPage({viewport:{width:1024,height:1024},deviceScaleFactor:1});
 await page.setContent(`<style>body{margin:0;background:#F3F4F8}svg{display:block}</style>${svg('#3155D9')}`);
 const box=await page.locator('svg > g').evaluate(el=>{const b=el.getBBox();return{x:b.x,y:b.y,width:b.width,height:b.height}});
 await page.screenshot({path:path.join(dir,'benchmate-soft-joint-preview.png')});
 const symmetry=await page.evaluate(async source=>{
  const img=new Image();img.src='data:image/svg+xml;charset=utf-8,'+encodeURIComponent(source);await img.decode();
  const c=document.createElement('canvas');c.width=c.height=1024;const ctx=c.getContext('2d');ctx.drawImage(img,0,0,1024,1024);
  const a=ctx.getImageData(0,0,1024,1024).data;let maximumAlphaDifference=0,antialiasedEdgeDifferences=0,opaqueVsTransparentMismatches=0;
  for(let i=0;i<1024*1024;i++){const first=a[i*4+3],second=a[(1024*1024-1-i)*4+3],difference=Math.abs(first-second);maximumAlphaDifference=Math.max(maximumAlphaDifference,difference);if(difference>2)antialiasedEdgeDifferences++;if(difference===255)opaqueVsTransparentMismatches++;}
  return{maximumAlphaDifference,antialiasedEdgeDifferences,opaqueVsTransparentMismatches,note:'Chromium may antialias rotated circular edges differently; exact vector symmetry is guaranteed by the rotation transform.'};
 },svg('#3155D9'));
 const checks={bounds:box,boundsCorrect:box.x===48&&box.y===48&&box.width===160&&box.height===160,anchorsOnGrid:anchors.every(p=>p.every(v=>v%8===0)),circleCentresAndRadiiOnGrid:circles.every(p=>p.every(v=>v%8===0)),exactSymmetryByConstruction:true,rotationCentre:[128,128],rasterSymmetry:symmetry};
 await fs.writeFile(path.join(dir,'geometry-checks.json'),JSON.stringify(checks,null,2));
 if(!checks.boundsCorrect||!checks.anchorsOnGrid||!checks.circleCentresAndRadiiOnGrid||symmetry.opaqueVsTransparentMismatches)throw Error('Geometry verification failed: '+JSON.stringify(checks));
 await page.setViewportSize({width:1600,height:1000});
 await page.goto(pathToFileURL(path.join(dir,'benchmate-soft-joint-construction.svg')).href);
 await page.screenshot({path:path.join(dir,'benchmate-soft-joint-construction.png')});
 console.log(JSON.stringify(checks));
}finally{await browser.close()}
