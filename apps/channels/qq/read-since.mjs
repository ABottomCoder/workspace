// Contract verb: read-since. Reads the conversation from the transcript the listener keeps
// (onebot.mjs), after the per-app cursor, then advances it. Run from the runtime dir (or `app read`).
//
//   read-since.mjs <conv>            new messages since the cursor (at most READ_MAX, default 60), advance
//   read-since.mjs <conv> --peek     same, don't advance
//   read-since.mjs <conv> --reset    forget the cursor
//   read-since.mjs <conv> --last N   the last N messages regardless of the cursor (cursor unchanged)
//   read-since.mjs --list-direct     private-chat conversation ids in the cursor store
// Rows: `[<epoch ts>] <who>(<qq>) #<message id>: <text>`, `bot` as who for the app's own posts;
// `↩#<id>` marks a quote-reply, `[blocked]` a user on the blocklist. Answer a specific message
// with `send --thread <message id>`.
// First read (no cursor): the last FIRST_READ (30) messages.
import { readFileSync, writeFileSync } from 'node:fs';
import { readRows, blocked } from './onebot.mjs';

const CURSORS = './.read-cursors.json';
const READ_MAX = Number(process.env.READ_MAX || 60);
const FIRST_READ = 30;
const load = () => { try { return JSON.parse(readFileSync(CURSORS, 'utf8')); } catch { return {}; } };
const save = (c) => writeFileSync(CURSORS, JSON.stringify(c, null, 2) + '\n');

if (process.argv[2] === '--list-direct') {
  for (const k of Object.keys(load())) if (k.startsWith('u')) console.log(k);
  process.exit(0);
}
const conv = process.argv[2];
if (!conv) { console.error('Usage: read-since.mjs <conv> [--peek|--reset] | --list-direct'); process.exit(1); }
const cursors = load();
if (process.argv.includes('--reset')) { delete cursors[conv]; save(cursors); console.error(`[cursor] ${conv} reset`); process.exit(0); }

const fmt = (r) => `[${r.ts}] ${r.self ? 'bot' : `${r.name}(${r.user})${blocked(r.user) ? ' [blocked]' : ''}`} #${r.id}${r.reply_to ? ` ↩#${r.reply_to}` : ''}: ${String(r.text).replace(/\n/g, ' ⏎ ')}`;
const li = process.argv.indexOf('--last');
if (li > 0) {
  const n = Math.min(Number(process.argv[li + 1]) || 50, 300);
  const rows = readRows(7).filter((r) => r.conv === conv).slice(-n);
  if (!rows.length) console.log('(no messages recorded yet)');
  for (const r of rows) console.log(fmt(r));
  process.exit(0);
}

// Cursor = {ts, ids at that ts}: several messages can share one second.
const cur = cursors[conv];
const rows = readRows(cur ? Math.max(2, Math.ceil((Date.now() / 1000 - cur.ts) / 86400) + 1) : 2)
  .filter((r) => r.conv === conv)
  .filter((r) => !cur || r.ts > cur.ts || (r.ts === cur.ts && !cur.ids.includes(r.id)));
const shown = cur ? rows.slice(-READ_MAX) : rows.slice(-FIRST_READ);
if (shown.length < rows.length) console.log(`(${rows.length - shown.length} earlier new message(s) not shown — grep the transcript for them)`);
if (rows.length === 0) console.log(`(no new messages since ${cur ? new Date(cur.ts * 1000).toISOString() : 'start'})`);
for (const r of shown) {
  console.log(fmt(r));
}
if (!process.argv.includes('--peek') && rows.length) {
  const last = rows[rows.length - 1].ts;
  cursors[conv] = { ts: last, ids: rows.filter((r) => r.ts === last).map((r) => r.id).concat(cur && cur.ts === last ? cur.ids : []) };
  save(cursors);
}
