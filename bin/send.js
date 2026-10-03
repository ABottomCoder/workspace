// Reply / send AS the bot (uses the bot token
// — NOT as your user). Use this to answer events the Monitor pushed.
//
// Usage:
//   node send.js --channel <channel_id> "your message"
//   node send.js --user <user_id> "your message"        # opens a bot<->user DM first
//   node send.js --channel <id> --thread <ts> "reply in thread"
//
// Examples:
//   node send.js --channel C0XXXXXXX "on it"
//   node send.js --user U0XXXXXXX "hi"

import 'dotenv/config';
import { WebClient } from '@slack/web-api';

const args = process.argv.slice(2);
function flag(name) {
  const i = args.indexOf(name);
  return i >= 0 ? args[i + 1] : null;
}
const channelArg = flag('--channel');
const userArg = flag('--user');
const thread = flag('--thread');
// message = everything that isn't a flag or a flag's value
const consumed = new Set();
['--channel', '--user', '--thread'].forEach((f) => {
  const i = args.indexOf(f);
  if (i >= 0) { consumed.add(i); consumed.add(i + 1); }
});
const message = args.filter((_, i) => !consumed.has(i)).join(' ').trim();

if ((!channelArg && !userArg) || !message) {
  console.error('Usage: node send.js (--channel <id> | --user <id>) [--thread <ts>] "message"');
  process.exit(1);
}

const web = new WebClient(process.env.SLACK_BOT_TOKEN);

(async () => {
  let channel = channelArg;
  if (userArg) {
    const open = await web.conversations.open({ users: userArg });
    channel = open.channel.id;
  }
  const r = await web.chat.postMessage({
    channel,
    text: message,
    ...(thread ? { thread_ts: thread } : {}),
  });
  console.log(`sent -> channel ${channel} ts ${r.ts}`);
})().catch((e) => {
  console.error('FAIL', e.data?.error || e.message);
  process.exit(1);
});
