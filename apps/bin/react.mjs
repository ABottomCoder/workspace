// Acknowledge a Slack message with a reaction, so the sender sees at once that the app received it.
// Called by wait-event.sh right after an event is handed to the session (not when the listener merely
// logs it): the reaction means "the Claude session has it", which is what the sender wants to know.
//
// Input: one `[slack-event] {json}` line on stdin. Run from the app's .runtime dir (reads ./.env).
// ACK_REACTION in .env picks the emoji name (default "eyes"); set it empty to disable.
// Needs the reactions:write scope. Failures are logged and ignored — an ack must never block anything.
import 'dotenv/config';
import { WebClient } from '@slack/web-api';

const name = process.env.ACK_REACTION ?? 'eyes';
if (!name) process.exit(0);

let raw = '';
for await (const chunk of process.stdin) raw += chunk;
let ev;
try { ev = JSON.parse(raw.replace(/^\[slack-event\]\s*/, '')); } catch { process.exit(0); }
if (!ev?.channel || !ev?.ts) process.exit(0);

try {
  await new WebClient(process.env.SLACK_BOT_TOKEN).reactions.add({ channel: ev.channel, timestamp: ev.ts, name });
} catch (e) {
  const err = e?.data?.error || e?.message;
  if (err !== 'already_reacted') console.error(`[react] ${err}${err === 'missing_scope' ? ' — add reactions:write to the app and reinstall it' : ''}`);
}
