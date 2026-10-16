import fs from 'node:fs';
import path from 'node:path';

// The original is retained so every revision is recoverable. The output HTML
// embeds all fonts and SVGs and can be presented without a network connection.
const root = process.cwd();
const assets = path.join(root, 'docs/brand-guide/assets');
let html = fs.readFileSync('docs/evidence/brand-guide/original.html', 'utf8');
const data = (mime, value) => `data:${mime};base64,${Buffer.from(value).toString('base64')}`;

// The wordmark is an editable, outlined SVG with no runtime font dependency.
const logoPath = path.join(assets, 'benchmate-wordmark.svg');

// Ordered dithering of analytic shapes. Each slide has its own geometry;
// these are native SVG graphics, not crops of a shared bitmap.
const bayer = [[0,8,2,10],[12,4,14,6],[3,11,1,9],[15,7,13,5]];
function artwork(kind) {
  let blue = '', lime = '';
  const clamp = v => Math.max(0, Math.min(1, v));
  for (let y=0; y<360; y+=4) for (let x=0; x<840; x+=4) {
    const u=x/840, v=y/360;
    let tone=0, accent=false;
    if (kind==='orbit') {
      const dx=(u-.56), dy=(v-.52);
      const a=dx*.93+dy*.25, b=-dx*.32+dy*.85;
      const radius=Math.sqrt((a/.43)**2+(b/.45)**2);
      const band=Math.exp(-(((radius-1)/.24)**2));
      tone=band*(.35+.55*clamp(.5+a-b));
      accent=radius>.88 && radius<1.13 && a>.18 && b<.07;
      if (accent) tone*=.9;
    } else if (kind==='ribbons') {
      const wave=.18*Math.sin(u*6.2-1.2);
      const dist=Math.min(...[.22,.49,.76].map(c=>Math.abs(v-c-wave)));
      tone=Math.exp(-((dist/.075)**2))*(.23+.65*u);
      accent=v>.58+wave && v<.82+wave && u>.7;
    } else {
      // Three folded, isometric planes with different shading directions.
      const X=(u-.5)*2.25, Y=(v-.52)*1.75;
      if (Math.abs(X)+Math.abs(Y)<.85) {
        tone=.22+.52*clamp(.5+X-Y);
        accent=Y<0 && X>0;
      }
      if (Y>.08 && Y<.66 && Math.abs(X-.49)<.26) tone=Math.max(tone,.65-.4*(Y-.08));
      if (Y>-.54 && Y<.05 && Math.abs(X+.62)<.18) tone=Math.max(tone,.2+.35*(Y+.54));
    }
    if (tone>(bayer[(y/4)%4][(x/4)%4]+.5)/16) {
      const segment=`M${x} ${y}h3v3h-3z`;
      if(accent) lime+=segment; else blue+=segment;
    }
  }
  const svg=`<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 840 360"><title>${kind==='orbit'?'Dithered orbital sculpture':kind==='ribbons'?'Dithered flowing ribbons':'Dithered folded planes'}</title><path fill="#3155D9" d="${blue}"/><path fill="#D6E879" d="${lime}"/></svg>`;
  fs.writeFileSync(path.join(assets, `dither-${kind}.svg`), svg);
  return data('image/svg+xml',svg);
}
const art = Object.fromEntries(['orbit','ribbons','facets'].map(k=>[k,artwork(k)]));
const fontFaces = [
  ['Space Grotesk','SpaceGrotesk.ttf','300 700'],
  ['Space Mono','SpaceMono-Regular.ttf','400'],
  ['Space Mono','SpaceMono-Bold.ttf','700'],
  ['Silkscreen','Silkscreen-Regular.ttf','400'],
].map(([family,file,weight])=>`@font-face{font-family:'${family}';font-style:normal;font-weight:${weight};font-display:swap;src:url('${data('font/ttf',fs.readFileSync(path.join(assets,file)))}') format('truetype');}`).join('\n');
html = html.replace(/@font-face\s*\{[^}]*\}/g,'');
html = html.replace('<style>','<style>\n'+fontFaces);
html = html.replace(/;--art:url\('[^']*'\)/, '');
html = html.replaceAll("'Unbounded'", "'Space Grotesk'").replaceAll('Unbounded', 'Space Grotesk');
html = html.replaceAll("'Azeret Mono'", "'Space Mono'").replaceAll('Azeret Mono', 'Silkscreen');
html = html.replaceAll('Onest', "'Space Mono'");
html = html.replace(/<img src="data:image\/png;base64,[^"]*" alt="BenchMate" class="custom-wordmark">/g,
  `<img src="${data('image/svg+xml',fs.readFileSync(logoPath))}" alt="BenchMate" class="custom-wordmark">`);

const columns = `<section class="type-columns">
<div class="type-column"><div class="type-top"><b>Space Grotesk</b><span>01</span></div><div class="glyph space">Aa</div><div class="alphabet space">ABCDEFGHIJKLM<br>nopqrstuvwxyz 0123456789</div><div class="type-rule"></div><h2>Headings &amp; subtitles</h2><p>Bold for confident headlines. Medium for subtitles, section headings and controls.</p><div class="weights"><strong>BOLD 700</strong> / MEDIUM 500</div></div>
<div class="type-column"><div class="type-top"><b>Space Mono</b><span>02</span></div><div class="glyph inter">Aa</div><div class="alphabet inter">ABCDEFGHIJKLM<br>nopqrstuvwxyz 0123456789</div><div class="type-rule"></div><h2>Body copy &amp; guidance</h2><p>Instructions, descriptions and reading text. Give every line room to breathe.</p><div class="weights">REGULAR 400 / <strong>BOLD 700</strong></div></div>
<div class="type-column"><div class="type-top"><b>Silkscreen</b><span>03</span></div><div class="glyph plex">Aa</div><div class="alphabet plex">ABCDEFGHIJKLM<br>nopqrstuvwxyz 0123456789</div><div class="type-rule"></div><h2>A pixel accent</h2><p>Short step labels, dimensions and technical moments. Use sparingly; keep prose in Space Mono.</p><div class="weights">REGULAR 400 / SHORT LABELS ONLY</div></div>
</section>`;
html = html.replace(/<section class="type-columns">[\s\S]*?<\/section>/,columns);
html = html.replace('Heading specimen / 29 px','Bold heading / 36 px')
  .replace('Interface specimen / 17 px','Body specimen / 16 px')
  .replace('Status specimen / 12 px','Pixel status / 16 px')
  .replace('One display voice. One reading voice. One technical voice.','Grotesk for hierarchy. Mono for reading. Pixels for precision.')
  .replace('Use pixel density to create tone. Keep patterns outside reading areas.','Orbit, ribbons, folded planes. Vary the form; keep the same pixel language.');

// Copy revision: title-case every title/subtitle; the decimal is a version.
html = html.replace('<span>BENCHMATE</span><span>2026 / EDITION 01</span>', '<span>Team 103</span>')
  .replace('<div class="cover-baseline" aria-hidden="true"></div>', '<div class="cover-baseline" aria-hidden="true"></div><div class="cover-version">Branding Guide 0.5</div>')
  .replace('Expressive headings.<br>Readable guidance. Precise labels.', 'Three Complementary Typefaces Bring Character, Clarity And Precision To Every Project')
  .replace('A little guidance for your next creation.', 'A Little Guidance For Your Next Creation')
  .replace('Your ideas.<br>A helping hand.', 'Your Ideas<br>A Helping Hand')
  .replaceAll('Visual identity', 'Visual Identity')
  .replace('02 / Color &amp; usage', '02 / Color Palette');
const titleCase = value => value.split(/(<[^>]+>|&[^;]+;)/g).map(part => /^(<|&)/.test(part) ? part : part.replaceAll('.', '').replace(/\b[a-z]/g, c => c.toUpperCase())).join('');
html = html.replace(/(<h[12][^>]*>)([\s\S]*?)(<\/h[12]>)/g, (_,open,text,close)=>open+titleCase(text)+close);
html = html.replace(/(<(?:span|div) class="(?:cover-heading|sample-title|label)">)([\s\S]*?)(<\/(?:span|div)>)/g, (_,open,text,close)=>open+titleCase(text)+close);

// Replace usage prose and interface specimens with five tonal families.
const palette = [
  {name:'Electric Blue',hex:'#3155D9',ink:'#FFFFFF',descriptor:'Confident Energy: Primary Actions, Active Navigation',tones:['#E0E6FC','#A8B8F3','#6B86E8','#2542B1','#182C7A']},
  {name:'Acid Lime',hex:'#D6E879',ink:'#292733',descriptor:'Fresh Sparks: Accent Markers, Campaign Highlights',tones:['#F3F8D7','#E6F1AC','#BDCE62','#8D9C41','#5E6927']},
  {name:'Cloud',hex:'#F3F4F8',ink:'#292733',descriptor:'Quiet Space: Page Backgrounds, Workspace Areas',tones:['#FCFCFE','#E5E6EE','#CDD0DD','#A7ACBF','#777F9A']},
  {name:'White',hex:'#FFFFFF',ink:'#292733',descriptor:'Pure Light: Reading Surfaces, Frosted Overlays',tones:['#FAFAFA','#F0F0F0','#DADADA','#BEBEBE','#969696']},
  {name:'Graphite',hex:'#292733',ink:'#FFFFFF',descriptor:'Grounded Contrast: Body Text, Interface Icons',tones:['#D4D2DB','#A9A6B5','#7E7A90','#514D63','#191820']},
];
const luminance = hex => {
  const values=hex.match(/[0-9a-f]{2}/gi).map(v=>parseInt(v,16)/255).map(v=>v<=.04045?v/12.92:((v+.055)/1.055)**2.4);
  return values[0]*.2126+values[1]*.7152+values[2]*.0722;
};
const toneInk = hex => luminance(hex)>.179?'#16151C':'#FFFFFF';
const paletteMarkup = `<section class="palette-families" aria-label="Five Color Families With Tints And Shades">${palette.map(color=>
  `<section class="palette-family" aria-label="${color.name}"><div class="palette-primary" style="background:${color.hex};color:${color.ink}"><h2>${color.name}</h2><span class="palette-hex">${color.hex}</span></div><div class="palette-tones" aria-label="${color.name} Light To Dark">${color.tones.map(hex=>`<div class="palette-tone" style="background:${hex};color:${toneInk(hex)}"><span>${hex}</span></div>`).join('')}</div><p class="palette-descriptor">${color.descriptor}</p></section>`
).join('')}</section>`;
const descriptorMarkup = paletteMarkup.replace(/(<p class="palette-descriptor">)([^:]+:)([^<]+)(<\/p>)/g, '$1<strong>$2</strong><span>$3</span>$4');
html = html.replace(/<section class="intro color-intro">[\s\S]*?<\/section>/, '<section class="intro color-intro"><h1>Color Palette</h1></section>')
  .replace(/<section class="color-grid">[\s\S]*?<\/section>\s*<section class="color-rules">[\s\S]*?<\/section>/, descriptorMarkup)
  .replace('White on Electric Blue / 6.1:1 contrast','TEAM 103 / BRANDING GUIDE 0.5');
const css = `
/* Revised typography and three independent abstract dither compositions. */
:root{--heading:'Space Grotesk',sans-serif;--body:'Space Mono',monospace;--technical:'Silkscreen',monospace}
html{-webkit-font-smoothing:antialiased}
body{font-family:var(--body)}
h1,h2,.cover-heading,.type-top b,.swatch .name{font-family:var(--heading);text-wrap:balance}
h1{font-size:72px;line-height:1.2;font-weight:700;letter-spacing:-3px}
.intro h1{padding-right:8px;line-height:1.3}
h2,.type-top b,.swatch .name,.cover-heading{font-weight:500}
p{text-wrap:pretty}
.cover{--art:url('${art.orbit}')}
#slide-1{--art:url('${art.ribbons}')}
#slide-2{--art:url('${art.facets}')}
.brand{width:212px;height:69px}.brand .custom-wordmark{width:212px}
.cover-wordmark{left:42px;right:42px;top:258px;height:266px}
.cover-wordmark img{width:100%;height:100%;object-fit:contain}
.cover-version{position:absolute;left:42px;top:548px;font:500 24px/1.3 var(--heading);letter-spacing:-.4px}
.cover-message{bottom:112px;max-width:800px}
.cover-message h1{font:700 48px/1.3 var(--heading);letter-spacing:-2px}
.cover-message p{font:400 18px/1.6 var(--body)}
.cover-heading{font-size:20px}
.cover-art{right:0;bottom:30px;width:675px;height:300px;background-size:710px 305px;background-position:center;background-repeat:no-repeat}
.cover-glass p{font:500 25px/1.3 var(--heading)}
.cover-glass .label{font:400 12px var(--technical);letter-spacing:0}
.intro::before{width:630px;background-size:630px 270px;background-position:center;background-repeat:no-repeat}
.intro::after{display:none}
.intro p{font:400 17px/1.5 var(--body);max-width:490px}
.color-intro h1{font-size:68px}
.color-intro p{font-size:15px;max-width:500px}
.type-top b{font:500 25px var(--heading)}
.type-top span{font-family:var(--technical);font-size:14px;color:var(--blue)}
.type-column h2{font:500 23px/1.2 var(--heading)}
.type-column p{font:400 15px/1.65 var(--body)}
.glyph.space{font:700 112px/1.05 var(--heading);letter-spacing:-7px;padding-top:0;padding-bottom:0}
.alphabet.space{font:500 19px/1.5 var(--heading);letter-spacing:.3px}
.glyph.inter{font-family:var(--body);font-size:108px;letter-spacing:-7px}
.alphabet.inter{font:400 15px/1.9 var(--body);letter-spacing:0}
.glyph.plex{font:400 100px/1.18 var(--technical);letter-spacing:-7px}
.alphabet.plex{font:400 14px/2 var(--technical);letter-spacing:0}
.weights{font-size:10px;line-height:1.6;margin-top:14px}
.weights strong{font-weight:700}
.glyph{height:120px;display:flex;align-items:center}
.alphabet.space,.alphabet.inter,.alphabet.plex{height:56px;line-height:28px}
.hierarchy .example .label{display:block;width:fit-content}
.sample-title{font:700 36px/1.15 var(--heading);letter-spacing:-1.2px}
.sample-body{font:400 16px/1.4 var(--body)}
.sample-mono{font:400 16px/1.5 var(--technical)}
.hierarchy .example::before{background-image:none}
.hierarchy .example:last-child::before{background-image:var(--art);opacity:.3;background-size:470px 200px;background-position:center}
.sample-body{background:var(--cloud);border-color:var(--rule)}
.sample-mono{background:rgba(255,255,255,.8)}
.usage h2{font:500 22px/1.15 var(--heading);letter-spacing:-.6px}
.usage p{font:400 13px/1.6 var(--body)}
.usage .avoid{font:400 10px/1.6 var(--body)}
.swatch .name{font:500 23px/1.15 var(--heading);letter-spacing:-.5px}
.swatch .hex{font:400 14px var(--technical)}
.specimen-stage::before{background-image:none}
.swatch.white::before{background-image:var(--art);background-size:265px 114px;background-position:center}
.specimen-glass,.glass-sample,.mini-action{font-family:var(--heading);font-weight:500;font-size:15px}
.dark-glass{font:400 13px var(--technical)}
.rule p{font-size:12px;line-height:1.65}
.palette-families{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));height:593px}
.palette-family{min-width:0;border-right:1px solid var(--rule)}
.palette-family:last-child{border-right:0}
.palette-primary{height:220px;padding:25px 24px;display:flex;flex-direction:column;justify-content:space-between}
.palette-primary h2{font:500 28px/1.2 var(--heading);letter-spacing:-.7px;margin:0}
.palette-hex{font:400 16px var(--technical)}
.palette-tones{height:275px;display:grid;grid-template-rows:repeat(5,1fr)}
.palette-tone{display:flex;align-items:center;justify-content:flex-end;padding:0 24px;border-top:1px solid rgba(41,39,51,.08);font:400 12px var(--body)}
.palette-descriptor{height:98px;margin:0;padding:14px 24px;border-top:1px solid var(--rule)}
.palette-descriptor strong{display:block;font:500 21px/1.25 var(--heading);margin-bottom:5px}
.palette-descriptor span{display:block;font:400 13px/1.5 var(--body);text-wrap:pretty}
.controls{height:44px}.controls button{min-width:40px;min-height:40px}
.count{font-variant-numeric:tabular-nums;min-width:170px}
@media(max-width:650px){.controls{gap:0}.nav{gap:4px}.count{min-width:155px;font-size:11px}}
`;
html=html.replace('</style>',css+'\n</style>');
const symbolSource=fs.readFileSync('docs/brand-guide/soft-joint-final/benchmate-soft-joint-blue.svg','utf8');
const motionSlide=fs.readFileSync('docs/brand-guide/logo-motion.html','utf8').replaceAll('@@WORDMARK@@',data('image/svg+xml',fs.readFileSync(logoPath))).replaceAll('@@LOGO@@',data('image/svg+xml',symbolSource));
html=html.replace('<article class="slide" hidden id="slide-1"',motionSlide+'\n<article class="slide" hidden id="slide-1"')
  .replace('01 / Typography','02 / Typography')
  .replace('02 / Color Palette','03 / Color Palette')
  .replace("['Cover','Typography','Color']","['Cover','Logo/Wordmark','Typography','Color','Walkthrough','Branding Mockups']")
  .replace("document.addEventListener('keydown',e=>{", "document.addEventListener('keydown',e=>{if(e.target.matches('input,textarea,select,[contenteditable]'))return;")
  .replace('This deliverable includes a cover plus sections 1 and 2.','This deliverable includes a cover, logo and wordmark construction, typography, color palette, a project walkthrough and branding mockups.');
html=html.replace('</style>',fs.readFileSync('docs/brand-guide/logo-motion.css','utf8')+'\n</style>');
const constructionVectors=JSON.stringify({wordmark:fs.readFileSync(logoPath,'utf8'),logo:symbolSource}).replaceAll('<','\\u003c');
html=html.replace('</body>',`<script type="application/json" id="construction-vector-data">${constructionVectors}</script>\n<script>${fs.readFileSync('docs/brand-guide/logo-motion.js','utf8')}</script>\n</body>`);
let mockups=fs.readFileSync('docs/brand-guide/mockups.html','utf8');
for (const [token,file,mime] of [
  ['SUBWAY_STILL','subway-poster.png','image/png'],
  ['STREET_STILL','street-poster.png','image/png'],
  ['VIDEO','subway-motion.mp4','video/mp4'],
  ['VIDEO_POSTER','subway-motion-poster.jpg','image/jpeg']
]) mockups=mockups.replaceAll(`@@${token}@@`,data(mime,fs.readFileSync(path.join(assets,'mockups',file))));
const navigationBoundary='</div></div><nav class="controls"';
if(!html.includes(navigationBoundary)) throw new Error('Slide insertion boundary missing');
html=html.replace(navigationBoundary,mockups+'\n'+navigationBoundary);
html=html.replace('</style>',fs.readFileSync('docs/brand-guide/mockups.css','utf8')+'\n</style>');
html=html.replace('</body>',`<script>${fs.readFileSync('docs/brand-guide/mockups.js','utf8')}</script>\n</body>`);
const walkthrough=fs.readFileSync('docs/brand-guide/walkthrough.html','utf8')
  .replaceAll('@@WALKTHROUGH_VIDEO@@',data('video/mp4',fs.readFileSync('docs/evidence/walkthrough/BenchMate-Walkthrough.mp4')))
  .replaceAll('@@WALKTHROUGH_POSTER@@',data('image/jpeg',fs.readFileSync(path.join(assets,'walkthrough-poster.jpg'))));
html=html.replace('<article class="slide branding-mockups"',walkthrough+'\n<article class="slide branding-mockups"');
html=html.replace(/<div class="source">[\s\S]*?<\/div>/,'');
html=html.replace('</style>',fs.readFileSync('docs/brand-guide/walkthrough.css','utf8')+'\n</style>');
html=html.replace('</body>',`<script>${fs.readFileSync('docs/brand-guide/walkthrough.js','utf8')}</script>\n</body>`);
fs.writeFileSync('BenchMate_Brand_Guide.html',html);
console.log(`Updated standalone guide: ${Math.round(Buffer.byteLength(html)/1024)} KB`);
