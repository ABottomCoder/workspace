// Contract verb: send. Posts AS the app (bot token), never as a person. Run from the runtime dir
// (or through `app send <id> …`).
//
//   send.js --conv <id> [--thread <ts>] "message"
//   send.js --conv <id> [--thread <ts>] --file msg.txt         message from a FILE
//   ... | send.js --conv <id> [--thread <ts>] --stdin          message from stdin
//   send.js --user <user_id> "message"                          opens a DM with that user first
//   send.js --conv <id> [--thread <ts>] --upload <path> [--title t] ["comment" | --file p | --stdin]
//                                                               file upload (needs files:write)
// (--channel is accepted as an alias of --conv.)
//
// PREFER --file / --stdin FOR ANYTHING NON-TRIVIAL. A message passed as a shell argument goes through
// the shell first: a backtick or $ inside it runs as command substitution and that span is silently
// DELETED from what is sent, while the send still reports success. --file never touches the shell.

import './env.mjs';
import { WebClient } from '@slack/web-api';
import { readFileSync } from 'node:fs';
import { basename } from 'node:path';

const args = process.argv.slice(2);
const VALUED = ['--conv', '--channel', '--user', '--thread', '--file', '--upload', '--title'];
const flag = (n) => { const i = args.indexOf(n); return i >= 0 ? args[i + 1] : null; };
const consumed = new Set();
for (const f of VALUED) { const i = args.indexOf(f); if (i >= 0) { consumed.add(i); consumed.add(i + 1); } }
if (args.includes('--stdin')) consumed.add(args.indexOf('--stdin'));

const convArg = flag('--conv') || flag('--channel');
const userArg = flag('--user');
const thread = flag('--thread');
const upload = flag('--upload');
const fileArg = flag('--file');
const message = fileArg
  ? readFileSync(fileArg, 'utf8').trim()
  : args.includes('--stdin')
    ? readFileSync(0, 'utf8').trim()
    : args.filter((_, i) => !consumed.has(i)).join(' ').trim();

if ((!convArg && !userArg) || (!message && !upload)) {
  console.error('Usage: send.js (--conv <id> | --user <id>) [--thread <ts>] ("message" | --file <path> | --stdin) [--upload <path> [--title t]]');
  process.exit(1);
}

const web = new WebClient(process.env.SLACK_BOT_TOKEN);

try {
  let conv = convArg;
  if (userArg) conv = (await web.conversations.open({ users: userArg })).channel.id;
  if (upload) {
    const r = await web.files.uploadV2({
      channel_id: conv, file: upload, filename: basename(upload), title: flag('--title') || basename(upload),
      ...(thread ? { thread_ts: thread } : {}), ...(message ? { initial_comment: message } : {}),
    });
    console.log(`uploaded -> conv ${conv} file ${r.files?.[0]?.files?.[0]?.id ?? r.files?.[0]?.id ?? '?'}`);
  } else {
    const r = await web.chat.postMessage({ channel: conv, text: message, ...(thread ? { thread_ts: thread } : {}) });
    console.log(`sent -> conv ${conv} ts ${r.ts}`);
  }
} catch (e) {
  console.error('FAIL', e.data?.error || e.message);
  process.exit(1);
}
