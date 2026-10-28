// Contract verb: listen (QQ via OneBot v11 forward WebSocket, e.g. NapCat on localhost).
//
// Every message in a listened conversation is written to the transcript (onebot.mjs); the session
// is woken once per BURST, not once per message: after a message, wait until the conversation has
// been quiet for APP_DEBOUNCE_MS (default 3000; max APP_DEBOUNCE_MAX_MS, 8000, from the first
// message), then emit one `[chat-event]` carrying the last message and `burst` = message count.
//   type app_mention  the burst @-mentions the app, replies to one of its messages, or contains one
//                     of APP_TRIGGER_WORDS (comma list) — the session should answer
//   type channel_message  anything else in a group — the session decides whether to join in
//   type dm           a private chat
// Users listed in <APP_MEMORY_DIR>/blocklist.txt (one id per line, `#` comments; the persona session
// maintains it) are recorded but never wake the session; the owner (APP_OWNER) can't be blocked.
// Also: `[ready]`, `[heartbeat] <ISO>` every 60 s and `[dropped] …` to stderr (the log).
// Exits 1 when no frame arrived for 120 s (NapCat sends a heartbeat every 30 s); the guardian restarts it.
//
// Run from the runtime dir.
import WebSocket from 'ws';
import { WS, TOKEN, call, convOf, list, record, rowFromEvent, readRows, atIds, replyTo, render, files, blocked } from './onebot.mjs';

process.on('unhandledRejection', (e) => console.error('[unhandledRejection]', e?.stack || e?.message || e));

const CONVS = list(process.env.APP_LISTEN_CONVS);
const TYPES = list(process.env.APP_LISTEN_TYPES);
const DM_USERS = list(process.env.APP_LISTEN_DM_USERS);
const TRIGGERS = list(process.env.APP_TRIGGER_WORDS).map((w) => w.toLowerCase());
const QUIET = Number(process.env.APP_DEBOUNCE_MS || 3000);
const MAX = Number(process.env.APP_DEBOUNCE_MAX_MS || 8000);

let self = null;
const ownIds = new Set();          // message ids the app posted (to spot replies to it)
const seen = new Set();            // message ids already recorded (backfill + live overlap)
for (const r of readRows(2)) { seen.add(r.id); if (r.self) ownIds.add(r.id); }

const bursts = new Map();          // conv -> {first, timer, count, mention, last}
function emit(conv) {
  const b = bursts.get(conv); bursts.delete(conv);
  if (!b) return;
  const ev = b.last;
  const type = ev.message_type === 'private' ? 'dm' : (b.mention ? 'app_mention' : 'channel_message');
  if (TYPES.length && !TYPES.includes(type)) {
    console.error(`[dropped] type=${type} conv=${conv} burst=${b.count} — not in APP_LISTEN_TYPES`);
    return;
  }
  process.stdout.write(`[chat-event] ${JSON.stringify({
    channel: 'qq', conv, conv_name: ev.group_name || null, type, user: String(ev.user_id), user_name: ev.sender?.card || ev.sender?.nickname || null,
    text: render(ev.message), ts: String(ev.message_id), thread: null, burst: b.count, mentioned: b.mention,
    files: files(ev.message), raw: ev,
  })}\n`);
}
function queue(conv, ev, mention) {
  const now = Date.now();
  const b = bursts.get(conv) || { first: now, count: 0, mention: false };
  clearTimeout(b.timer);
  b.count += 1; b.mention ||= mention; b.last = ev;
  const wait = Math.max(0, Math.min(mention ? QUIET / 2 : QUIET, b.first + MAX - now));
  b.timer = setTimeout(() => emit(conv), wait);
  bursts.set(conv, b);
}

function handle(ev) {
  if (ev.post_type !== 'message' && ev.post_type !== 'message_sent') return;
  const conv = convOf(ev);
  const allowed = ev.message_type === 'group'
    ? (CONVS.length === 0 || CONVS.includes(conv))
    : (DM_USERS.length === 0 || DM_USERS.includes(String(ev.user_id)));
  if (!allowed) { console.error(`[dropped] conv=${conv} user=${ev.user_id} — not in APP_LISTEN_*`); return; }
  const id = String(ev.message_id);
  if (seen.has(id)) return;
  seen.add(id);
  const row = rowFromEvent(ev, self);
  if (row.self) {                                    // own posts never wake the session; `send` records
    ownIds.add(id);                                  // them itself, so only posts made elsewhere (the
    if (!readRows(1).some((r) => r.id === id)) record(row);   // account's own QQ client) are added here
    return;
  }
  record(row);
  if (blocked(row.user)) { console.error(`[blocked] user=${row.user} conv=${conv} — recorded, no wake`); return; }
  const text = row.text.toLowerCase();
  const mention = atIds(ev.message).includes(String(self))
    || (replyTo(ev.message) != null && ownIds.has(String(replyTo(ev.message))))
    || TRIGGERS.some((w) => text.includes(w));
  queue(conv, ev, mention);
}

// Messages that arrived while disconnected (the guardian recycles the listener): record them, no wake.
async function backfill() {
  for (const conv of CONVS) {
    try {
      const d = await call('get_group_msg_history', { group_id: Number(conv.slice(1)), count: 50 });
      let n = 0;
      for (const m of d?.messages || []) {
        const id = String(m.message_id);
        if (seen.has(id)) continue;
        seen.add(id); m.message_type = 'group'; record(rowFromEvent(m, self)); n++;
      }
      if (n) console.error(`[backfill] ${conv}: ${n} message(s) recorded from the gap`);
    } catch (e) { console.error(`[backfill] ${conv}: ${e.message}`); }
  }
}

let lastFrame = Date.now();
setInterval(() => console.error(`[heartbeat] ${new Date().toISOString()}`), 60_000).unref();
setInterval(() => {
  if (Date.now() - lastFrame > 120_000) { console.error('[watchdog] no frame for 120 s — exiting for restart'); process.exit(1); }
}, 15_000).unref();

try {
  const me = await call('get_login_info');
  self = String(me.user_id);
  console.error(`[ready] logged in as ${me.nickname} (${self}); listening to ${CONVS.join(',') || 'all groups'}`);
} catch (e) {
  console.error(`[fatal] OneBot HTTP not reachable or rejected: ${e.message}`);
  process.exit(1);
}
await backfill();

const ws = new WebSocket(WS, { headers: TOKEN ? { authorization: `Bearer ${TOKEN}` } : {} });
ws.on('open', () => console.error('[ws] connected'));
ws.on('message', (data) => {
  lastFrame = Date.now();
  let ev; try { ev = JSON.parse(String(data)); } catch { return; }
  try { handle(ev); } catch (e) { console.error('[handler-error]', e.message); }
});
ws.on('close', (code) => { console.error(`[ws] closed ${code}`); process.exit(1); });
ws.on('error', (e) => { console.error(`[ws-error] ${e.message}`); process.exit(1); });
