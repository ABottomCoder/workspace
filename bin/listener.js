// Socket Mode listener — the "monitor/forwarder" half of the Discord-style bridge.
//
// Canonical fleet listener. Forwards @mentions + DMs, and ALSO can forward
// every plain message in channels the bot has been invited to (message.channels /
// message.groups are subscribed in manifest.yaml).
//
// It connects to Slack over a WebSocket (no public URL needed) and prints ONE
// line of stdout per relevant event. The Claude Code `Monitor` tool turns each
// stdout line into an event in the session, so there is zero polling.
//
// Emitted line format (parseable + human-readable):
//   [slack-event] {"type":"channel_message","channel":"C…","channel_name":"#general",
//                  "user":"U…","user_name":"<name>","text":"…","ts":"…","thread_ts":"…","permalink":"…"}
//
// Run: node listener.js   (expects SLACK_APP_TOKEN + SLACK_BOT_TOKEN in env / .env)

import 'dotenv/config';
import { SocketModeClient } from '@slack/socket-mode';
import { WebClient } from '@slack/web-api';

const appToken = process.env.SLACK_APP_TOKEN; // xapp-…  (app-level, connections:write)
const botToken = process.env.SLACK_BOT_TOKEN; // xoxb-…  (bot token)

if (!appToken || !botToken) {
  console.error('[fatal] SLACK_APP_TOKEN and SLACK_BOT_TOKEN are required');
  process.exit(1);
}

// Resilience: a stray async rejection inside the socket-mode client (a transient
// Slack API hiccup / a reconnect race) otherwise takes the WHOLE monitor down —
// Node exits 1 on an unhandled rejection, and the main-loop socket is fine, so
// crashing loses message capture for no reason. Log and keep the listener alive;
// the socket client reconnects on its own.
process.on('unhandledRejection', (e) => console.error('[unhandledRejection]', e && (e.stack || e.message || e)));
process.on('uncaughtException', (e) => console.error('[uncaughtException]', e && (e.stack || e.message || e)));

const web = new WebClient(botToken);

// Zombie-socket self-heal. A network blip can leave the socket-mode connection
// wedged: the client keeps logging "ping/pong wasn't received" and retrying
// forever, the Node PROCESS stays alive (so the while-loop wrapper never
// restarts it), and it silently misses messages — observed dead for DAYS after
// one blip. Those ping/pong-timeout warnings are the precise dying signal, so we
// intercept them via a custom logger: once the connection has been failing for
// >STALE_MS with no recovery (a real inbound frame clears it), exit(1) and let
// the wrapper restart with a fresh socket.
let dyingSince = null;
const STALE_SOCKET_MS = 90_000;
const healthLogger = {
  debug() {},
  info: (...a) => console.error('[sm]', ...a),
  warn: (...a) => {
    const msg = a.join(' ');
    console.error('[sm-warn]', msg);
    if (/wasn't received/i.test(msg) && !dyingSince) dyingSince = Date.now();
  },
  error: (...a) => console.error('[sm-error]', ...a),
  setLevel() {},
  getLevel: () => 'info',
  setName() {},
  getName: () => 'slack-sm',
};
const socket = new SocketModeClient({ appToken, logger: healthLogger });
// A real inbound frame (hello on reconnect, or any event) ⇒ the socket recovered.
socket.on('ws_message', () => { dyingSince = null; });
setInterval(() => {
  if (dyingSince && Date.now() - dyingSince > STALE_SOCKET_MS) {
    console.error(`[watchdog] socket wedged >${STALE_SOCKET_MS / 1000}s (ping/pong failing) — exiting for wrapper restart`);
    process.exit(1);
  }
}, 20_000).unref();

// Best-effort name caches so we don't hammer the API.
const userNames = new Map();
const channelNames = new Map();
let botUserId = null;

async function userName(id) {
  if (!id) return null;
  if (userNames.has(id)) return userNames.get(id);
  try {
    const r = await web.users.info({ user: id });
    const name = r.user?.profile?.display_name || r.user?.real_name || r.user?.name || id;
    userNames.set(id, name);
    return name;
  } catch { return id; }
}

async function channelName(id) {
  if (!id) return null;
  if (channelNames.has(id)) return channelNames.get(id);
  try {
    const r = await web.conversations.info({ channel: id });
    const name = r.channel?.is_im ? '(dm)' : (r.channel?.name ? `#${r.channel.name}` : id);
    channelNames.set(id, name);
    return name;
  } catch { return id; }
}

async function permalink(channel, ts) {
  try {
    const r = await web.chat.getPermalink({ channel, message_ts: ts });
    return r.permalink || null;
  } catch { return null; }
}

function emit(obj) {
  // One line = one Monitor event. Keep it on a single line.
  process.stdout.write(`[slack-event] ${JSON.stringify(obj)}\n`);
}

// Dedup: an @mention inside a channel fires BOTH app_mention AND message.channels
// for the same message. Emit it once (whichever event arrives first wins).
const seen = new Map(); // `${channel}:${ts}` -> expiry
const SEEN_TTL_MS = 60_000;
function alreadySeen(channel, ts) {
  const now = Date.now();
  for (const [k, exp] of seen) if (exp < now) seen.delete(k);
  const key = `${channel}:${ts}`;
  if (seen.has(key)) return true;
  seen.set(key, now + SEEN_TTL_MS);
  return false;
}

// Runaway bot↔bot loop guard: cap peer-bot events per rolling hour.
const BOT_EVENT_CAP = parseInt(process.env.MONITOR_BOT_EVENT_CAP || '30', 10);
const botEventTimes = [];
function botRateLimited() {
  const now = Date.now();
  while (botEventTimes.length && botEventTimes[0] < now - 3600_000) botEventTimes.shift();
  if (botEventTimes.length >= BOT_EVENT_CAP) { console.error('[loop-guard] peer-bot event dropped (hourly cap reached)'); return true; }
  botEventTimes.push(now);
  return false;
}

async function handleEvent(event) {
  // Ignore the bot's own posts and edit/delete/bot-subtype noise.
  // Exception: peer bots allowlisted in MONITOR_ALLOW_BOT_SENDERS (comma-sep
  // bot user ids U… and/or bot ids B…) pass through — enables bot↔bot
  // @-mention collaboration (e.g. a dev-bot↔QA-bot loop).
  if (!event) return;
  const ALLOW_BOTS = (process.env.MONITOR_ALLOW_BOT_SENDERS || '').split(',').map((s) => s.trim()).filter(Boolean);
  const fromPeerBot = !!(event.bot_id && (ALLOW_BOTS.includes(event.bot_id) || (event.user && ALLOW_BOTS.includes(event.user))));
  if (event.bot_id && !fromPeerBot) return;
  if (event.user && event.user === botUserId) return;
  if (event.subtype && !(fromPeerBot && event.subtype === 'bot_message')) return; // message_changed, message_deleted, channel_join, etc.
  if (fromPeerBot && botRateLimited()) return;

  // Shapes per the manifest: app_mention + message.im + message.channels + message.groups.
  const isDM = event.channel_type === 'im';
  const isChannelMsg = event.type === 'message' && (event.channel_type === 'channel' || event.channel_type === 'group');
  const type = event.type === 'app_mention' ? 'app_mention' : (isDM ? 'dm' : (isChannelMsg ? 'channel_message' : event.type));
  if (type !== 'app_mention' && type !== 'dm' && type !== 'channel_message') return;

  // Allowlists (empty = allow that whole shape):
  //   • MONITOR_ALLOW_TYPES    — event types to forward: app_mention, dm, channel_message
  //   • MONITOR_ALLOW_CHANNELS — channel ids whose messages/mentions get forwarded
  //   • MONITOR_ALLOW_DM_USERS — user ids whose DMs get forwarded
  const ALLOW_TYPES = (process.env.MONITOR_ALLOW_TYPES || '').split(',').map((s) => s.trim()).filter(Boolean);
  if (ALLOW_TYPES.length > 0 && !ALLOW_TYPES.includes(type)) return;
  const ALLOW_CH = (process.env.MONITOR_ALLOW_CHANNELS || '').split(',').map((s) => s.trim()).filter(Boolean);
  const ALLOW_DM_USERS = (process.env.MONITOR_ALLOW_DM_USERS || '').split(',').map((s) => s.trim()).filter(Boolean);
  const allowedChannel = (type === 'app_mention' || type === 'channel_message')
    && (ALLOW_CH.length === 0 || (event.channel && ALLOW_CH.includes(event.channel)));
  const allowedDM = type === 'dm' && (ALLOW_DM_USERS.length === 0 || (event.user && ALLOW_DM_USERS.includes(event.user)));
  if (!allowedChannel && !allowedDM) {
    // LOG THE DROP. This return used to be silent, and a silently-dropped
    // message is indistinguishable from "nobody wrote to me" — which is exactly
    // how example went unanswered for three days while every health check was
    // green (2026-08-31). The line is not forwarded as an event, so it does not
    // pollute the session; it just leaves a trace in the log so "am I actually
    // reachable?" is answerable.
    console.error(`[dropped] type=${type} user=${event.user || '?'} channel=${event.channel || '?'} — not in MONITOR_ALLOW_*`);
    return;
  }

  // One emit per message even when app_mention + message.channels both fire.
  if (type !== 'dm' && alreadySeen(event.channel, event.ts)) return;

  const [user_name, channel_name, link] = await Promise.all([
    event.user ? userName(event.user) : Promise.resolve((event.bot_profile && event.bot_profile.name) || 'bot'),
    channelName(event.channel),
    permalink(event.channel, event.ts),
  ]);

  emit({
    type,
    channel: event.channel,
    channel_name,
    user: event.user,
    user_name,
    text: event.text || '',
    ts: event.ts,
    thread_ts: event.thread_ts || null,
    permalink: link,
  });
}

socket.on('slack_event', async ({ ack, body }) => {
  // Always ack quickly so Slack doesn't retry.
  if (ack) { try { await ack(); } catch {} }
  // The inner Slack event lives at body.event (NOT a top-level `event` field).
  const inner = body?.event;
  if (inner) { try { await handleEvent(inner); } catch (e) { console.error('[handler-error]', e?.message); } }
});

socket.on('disconnect', () => console.error('[socket] disconnected, reconnecting…'));
socket.on('error', (e) => console.error('[socket-error]', e?.message || e));

// Heartbeat: the log always grows, so "idle" vs "hung" is distinguishable at a
// glance (`tail -3 <name>-listener.log` — a heartbeat within ~60s = healthy).
setInterval(() => console.error(`[heartbeat] ${new Date().toISOString()}`), 60_000).unref();

(async () => {
  try {
    const auth = await web.auth.test();
    botUserId = auth.user_id;
    console.error(`[ready] connected as ${auth.user} (${auth.user_id}) in ${auth.team}`);
  } catch (e) {
    console.error('[fatal] auth.test failed — check SLACK_BOT_TOKEN:', e?.data?.error || e?.message);
    process.exit(1);
  }
  await socket.start();
})();
