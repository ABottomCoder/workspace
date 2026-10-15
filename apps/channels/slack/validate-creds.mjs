// Contract verb: validate-creds. Checks the app's Slack tokens; prints "<bot> <user_id> in <team>"
// and exits 0, or prints the error and exits 1. Run from the app's runtime dir.
import './env.mjs';
import { WebClient } from '@slack/web-api';

const app = process.env.SLACK_APP_TOKEN || '', bot = process.env.SLACK_BOT_TOKEN || '';
if (!app.startsWith('xapp-')) { console.error('SLACK_APP_TOKEN missing or not an xapp- token'); process.exit(1); }
if (!bot.startsWith('xoxb-')) { console.error('SLACK_BOT_TOKEN missing or not an xoxb- token'); process.exit(1); }
const r = await new WebClient(bot).auth.test().catch((e) => ({ ok: false, error: e.data?.error || e.message }));
if (!r.ok) { console.error(`Slack rejected the bot token: ${r.error}`); process.exit(1); }
console.log(`${r.user} ${r.user_id} in ${r.team}`);
