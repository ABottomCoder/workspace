// Contract verb (optional): react. Acknowledges a message with a reaction so the sender sees at once
// that the app's session has it. Called by wait-event.sh right after an event is handed to the
// session (not when the listener merely logs it).
// Input: one `[chat-event] {json}` (or legacy `[slack-event]`) line on stdin. Run from the runtime dir.
// APP_ACK_REACTION picks the emoji name (default "eyes"); set it empty to disable. Needs reactions:write.
// Failures are logged and ignored — an ack must never block anything.
import './env.mjs';
import { WebClient } from '@slack/web-api';

const name = process.env.APP_ACK_REACTION ?? 'eyes';
if (!name) process.exit(0);

let raw = '';
for await (const chunk of process.stdin) raw += chunk;
let ev;
try { ev = JSON.parse(raw.replace(/^\[(chat|slack)-event\]\s*/, '')); } catch { process.exit(0); }
const conv = ev?.conv || ev?.channel;
if (!conv || !ev?.ts) process.exit(0);

try {
  await new WebClient(process.env.SLACK_BOT_TOKEN).reactions.add({ channel: conv, timestamp: ev.ts, name });
} catch (e) {
  const err = e?.data?.error || e?.message;
  if (err !== 'already_reacted') console.error(`[react] ${err}${err === 'missing_scope' ? ' — add reactions:write to the app and reinstall it' : ''}`);
}
