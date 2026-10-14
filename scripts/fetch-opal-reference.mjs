import {writeFile} from 'node:fs/promises';
const response=await fetch('https://media.weavy.ai/image/upload/v1791947893/uploads/RjA4KfH9v0eVz56zC2LruMUpYXG2/ev2c9xsaqsetmmfzbqyz.png');
if(!response.ok)throw new Error(`Reference download HTTP ${response.status}`);
const bytes=Buffer.from(await response.arrayBuffer());
await writeFile(new URL('../docs/design/revisions/benchmate-20261013-opal-r3/references/images/img-01-opal-frost-board.png',import.meta.url),bytes);
console.log(`Downloaded ${bytes.length} bytes`);
