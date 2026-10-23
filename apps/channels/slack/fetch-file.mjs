// Contract verb (optional): fetch-file. Downloads a file shared with the app (an id from an
// event's `files`) into .runtime/files/ and prints the local path. Needs files:read.
// Usage (from the runtime dir): fetch-file.mjs <file id F…> [more ids…]
// The bot token goes only into the request header; it is never printed.
import './env.mjs';
import { WebClient } from '@slack/web-api';
import { mkdirSync, writeFileSync } from 'node:fs';
import { basename, resolve } from 'node:path';

const ids = process.argv.slice(2);
if (!ids.length) { console.error('usage: fetch-file <file id> [more ids]'); process.exit(2); }
const token = process.env.SLACK_BOT_TOKEN;
const web = new WebClient(token);
const dir = resolve('files');
mkdirSync(dir, { recursive: true, mode: 0o700 });

let failed = 0;
for (const id of ids) {
  try {
    const { file } = await web.files.info({ file: id });
    const url = file.url_private_download || file.url_private;
    if (!url) throw new Error('no download url (external or deleted file)');
    const r = await fetch(url, { headers: { Authorization: `Bearer ${token}` } });
    const type = r.headers.get('content-type') || '';
    // Without files:read Slack answers with its HTML login page and status 200.
    if (!r.ok || (type.startsWith('text/html') && !String(file.mimetype).startsWith('text/html'))) {
      throw new Error(`download refused (HTTP ${r.status}, ${type}); check files:read and that the app can see the conversation`);
    }
    const out = resolve(dir, `${id}-${basename(file.name || 'file').replace(/[^\w.-]+/g, '_')}`);
    writeFileSync(out, Buffer.from(await r.arrayBuffer()), { mode: 0o600 });
    console.log(`${id} -> ${out} (${file.mimetype || '?'}, ${file.size ?? '?'} bytes)`);
  } catch (e) {
    failed++;
    console.error(`${id}: ${e?.data?.error || e.message}`);
  }
}
process.exit(failed ? 1 : 0);
