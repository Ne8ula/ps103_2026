// Copy the supplied brand masters; never approximate the wordmark with live type.
import fs from 'node:fs/promises';
import {createHash} from 'node:crypto';
const guide = await fs.readFile('BenchMate_Brand_Guide.html', 'utf8');
const assets = [
  ['docs/brand-guide/assets/SpaceGrotesk.ttf', 'public/fonts/SpaceGrotesk.ttf'],
  ['docs/brand-guide/assets/SpaceMono-Regular.ttf', 'public/fonts/SpaceMono-Regular.ttf'],
  ['docs/brand-guide/assets/SpaceMono-Bold.ttf', 'public/fonts/SpaceMono-Bold.ttf'],
  ['docs/brand-guide/assets/Silkscreen-Regular.ttf', 'public/fonts/Silkscreen-Regular.ttf'],
  ...['SpaceGrotesk', 'SpaceMono', 'Silkscreen'].map(name => [`docs/brand-guide/assets/${name}-OFL.txt`, `public/licenses/${name}-OFL.txt`]),
  ['docs/brand-guide/assets/benchmate-wordmark.svg', 'public/brand/benchmate-wordmark.svg'],
  ['docs/brand-guide/soft-joint-final/benchmate-soft-joint-tight.svg', 'public/brand/benchmate-logo.svg'],
  ['docs/brand-guide/soft-joint-final/benchmate-soft-joint-blue.svg', 'public/favicon.svg'],
];
const embedded = [...guide.matchAll(/data:[^;,]+;base64,([A-Za-z0-9+/=]+)/g)].map(match => Buffer.from(match[1], 'base64'));
const hashes = [];
for (const [source, target] of assets) {
  const bytes = await fs.readFile(source);
  if ((source.endsWith('.ttf') || source.endsWith('benchmate-wordmark.svg')) && !embedded.some(asset => asset.equals(bytes))) throw new Error(`Master differs from the supplied guide: ${source}`);
  await fs.mkdir(target.slice(0, target.lastIndexOf('/')), {recursive:true});
  await fs.writeFile(target, bytes);
  hashes.push({source, target, sha256:createHash('sha256').update(bytes).digest('hex')});
}
await fs.writeFile('public/brand/provenance.json', JSON.stringify({guide:'BenchMate_Brand_Guide.html', assets:hashes}, null, 2)+'\n');
console.log('Copied 10 brand assets; all four fonts and the wordmark match the guide exactly.');
