import {mkdir, writeFile} from 'node:fs/promises';
const directory = new URL('../docs/design/revisions/benchmate-20261013-weave-r1/references/images/', import.meta.url);
await mkdir(directory, {recursive:true});
const response = await fetch('https://media.weavy.ai/image/upload/v1791939120/uploads/RjA4KfH9v0eVz56zC2LruMUpYXG2/w6z2byvhifiv36o5d2yx.png');
if(!response.ok) throw new Error(`Reference download HTTP ${response.status}`);
const bytes = Buffer.from(await response.arrayBuffer());
await writeFile(new URL('img-01-benchmate-state-board.png',directory), bytes);
console.log(`Downloaded ${bytes.length} bytes`);
