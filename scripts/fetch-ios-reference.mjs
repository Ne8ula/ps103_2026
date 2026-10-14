import {writeFile} from 'node:fs/promises';
const response = await fetch('https://media.weavy.ai/image/upload/v1791940743/uploads/RjA4KfH9v0eVz56zC2LruMUpYXG2/gzkrpxmbgvokgotp7duj.png');
if (!response.ok) throw new Error(`Reference download HTTP ${response.status}`);
const bytes = Buffer.from(await response.arrayBuffer());
await writeFile(new URL('../docs/design/revisions/benchmate-20261013-ios-r2/references/images/img-01-ios-material-board.png', import.meta.url), bytes);
console.log(`Downloaded ${bytes.length} bytes`);
