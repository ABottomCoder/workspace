// Contract verb: read-since — the one sanctioned way for an app to read a conversation.
// Reads from the last-read cursor to newest (incl. thread replies, also under parents older than
// the cursor), then advances the cursor. Every call returns exactly the messages since you last read.
//
// Run from the app's runtime dir (or through `app read <id> …`):
//   read-since.mjs <conv>            read new messages, advance cursor
//   read-since.mjs <conv> --peek     show new messages, DON'T advance
//   read-since.mjs <conv> --reset    forget the cursor for this conversation
//   read-since.mjs --list-direct     print the direct-message conversation ids in the cursor store
//                                    (wait-event.sh's default catch-up set)
// Output rows: `[<ts>]( ↳)? <who>: <text>` — ts in epoch seconds; "bot" = posted with a bot token.
//
// Cursor store: ./.read-cursors.json = { "<conv>": "<ts>", ... } (per app)
// First read of a conversation (no cursor yet): shows the last FIRST_READ messages and initialises
// the cursor — it does NOT dump full history.

import './env.mjs';
import { WebClient } from '@slack/web-api';
import { readFileSync, writeFileSync } from 'fs';

const FIRST_READ = 50;
// Replies posted after the cursor under a parent from BEFORE the cursor are invisible to
// conversations.history (it returns top-level messages only) — mentions inside an older thread
// were once missed for hours this way.
// Parents up to THREAD_LOOKBACK_DAYS before the cursor are scanned for newer replies.
const THREAD_LOOKBACK_DAYS = Number(process.env.THREAD_LOOKBACK_DAYS || 14);
const THREAD_LOOKBACK_PAGES = 5;   // x200 parents; caps the cost on busy channels
const CURSORS = './.read-cursors.json';

if (process.argv[2] === '--list-direct') {
  try { for (const k of Object.keys(JSON.parse(readFileSync(CURSORS, 'utf8')))) if (k.startsWith('D')) console.log(k); } catch {}
  process.exit(0);
}
const channel = process.argv[2];
const peek = process.argv.includes('--peek');
const reset = process.argv.includes('--reset');
if (!channel) { console.error('Usage: read-since.mjs <conv> [--peek|--reset] | --list-direct'); process.exit(1); }

const web = new WebClient(process.env.SLACK_BOT_TOKEN);
const load = () => { try { return JSON.parse(readFileSync(CURSORS, 'utf8')); } catch { return {}; } };
const save = (c) => writeFileSync(CURSORS, JSON.stringify(c, null, 2) + '\n');

const cursors = load();
if (reset) { delete cursors[channel]; save(cursors); console.error(`[cursor] ${channel} reset`); process.exit(0); }
const since = cursors[channel];

const nameCache = new Map();
async function name(uid) {
  if (!uid) return 'bot';
  if (nameCache.has(uid)) return nameCache.get(uid);
  let n = uid;
  try { const r = await web.users.info({ user: uid }); n = r.user?.profile?.display_name || r.user?.real_name || uid; } catch {}
  nameCache.set(uid, n); return n;
}

// main-channel messages from `since` (exclusive) to newest, paginated
async function fetchMain() {
  const out = []; let cur;
  const base = since ? { channel, oldest: since, inclusive: false, limit: 200 } : { channel, limit: FIRST_READ };
  do {
    const r = await web.conversations.history(cur ? { ...base, cursor: cur } : base);
    if (!r.ok) throw new Error(r.error);
    out.push(...r.messages);
    cur = r.response_metadata?.next_cursor;
    if (!since) break;               // first read: newest FIRST_READ only
  } while (cur);
  return out.reverse();              // history is newest-first → oldest-first
}

async function fetchReplies(ts) {
  try { const r = await web.conversations.replies({ channel, ts, limit: 200 }); return r.ok ? r.messages.filter(m => m.ts !== ts) : []; }
  catch { return []; }
}

const main = await fetchMain();
const rows = [];
let newest = since || '0';
const bump = (ts) => { if (Number(ts) > Number(newest)) newest = ts; };

for (const m of main) {
  rows.push({ ts: m.ts, who: await name(m.user), text: m.text || '', thread: false });
  bump(m.ts);
  if (m.reply_count && m.thread_ts === m.ts) {           // parent with replies → pull thread
    for (const rp of await fetchReplies(m.ts)) {
      if (since && Number(rp.ts) <= Number(since)) continue;   // skip already-seen replies
      rows.push({ ts: rp.ts, who: await name(rp.user), text: rp.text || '', thread: true });
      bump(rp.ts);
    }
  }
}
// Old parents (before the cursor) whose thread got replies after it.
if (since) {
  let cur, pages = 0;
  const base = { channel, latest: since, inclusive: true, oldest: String(Number(since) - THREAD_LOOKBACK_DAYS * 86400), limit: 200 };
  do {
    let r; try { r = await web.conversations.history(cur ? { ...base, cursor: cur } : base); } catch { break; }
    if (!r.ok) break;
    for (const m of r.messages) {
      if (!(m.reply_count && m.thread_ts === m.ts && Number(m.latest_reply || 0) > Number(since))) continue;
      for (const rp of await fetchReplies(m.ts)) {
        if (Number(rp.ts) <= Number(since)) continue;
        rows.push({ ts: rp.ts, who: await name(rp.user), text: rp.text || '', thread: true, parent: m.ts });
        bump(rp.ts);
      }
    }
    cur = r.response_metadata?.next_cursor;
  } while (cur && ++pages < THREAD_LOOKBACK_PAGES);
}

rows.sort((a, b) => Number(a.ts) - Number(b.ts));

if (rows.length === 0) console.log(`(no new messages since cursor ${since})`);
else for (const r of rows) console.log(`[${r.ts}]${r.thread ? '  ↳' : ''} ${r.who}: ${r.text.replace(/\n/g, ' ⏎ ')}${r.parent ? `   ⟨reply in older thread ${r.parent} — answer with --thread ${r.parent}⟩` : ''}`);

if (!peek && newest !== (since || '0')) {
  cursors[channel] = newest; save(cursors);
  console.error(`\n[cursor] ${channel} → ${newest}${since ? '' : ' (first read — cursor initialized)'}`);
} else if (peek) {
  console.error(`\n[peek] cursor unchanged (${since || 'none'})`);
}
