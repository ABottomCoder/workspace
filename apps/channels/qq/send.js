// Contract verb: send. Posts as the app's QQ account. Run from the runtime dir (or `app send <id> …`).
//
//   send.js --conv <g…|u…> [--thread <message id>] "text"      --thread = quote-reply that message
//   send.js --conv <id> [--thread <id>] (--file msg.txt | --stdin)
//   send.js --conv <id> [--at <qq>]… [--image <url|path>]… ["text" | --file | --stdin]
//   send.js --conv <id> --upload <path>                         a file (group file / private file)
//
// Local files (--upload, --image <path>) are sent base64-encoded: the endpoint usually runs in a
// container that can't see host paths. Upload limit 20 MB.
// Fuse: at most APP_SEND_CAP_PER_HOUR posts per rolling hour (default 30) — a runaway guard, not a
// tuning knob; ./.send-times.json holds the timestamps. Each post is recorded in the transcript.
import { readFileSync, statSync, writeFileSync } from 'node:fs';
import { basename, resolve } from 'node:path';
import { call, parseConv, record } from './onebot.mjs';

const args = process.argv.slice(2);
const consumed = new Set();
const all = (n) => { const out = []; args.forEach((a, i) => { if (a === n) { out.push(args[i + 1]); consumed.add(i); consumed.add(i + 1); } }); return out; };
const flag = (n) => all(n)[0] ?? null;
const conv = flag('--conv') || flag('--channel');
const thread = flag('--thread');
const fileArg = flag('--file');
const upload = flag('--upload');
const ats = all('--at');
const images = all('--image');
if (args.includes('--stdin')) consumed.add(args.indexOf('--stdin'));
const text = fileArg ? readFileSync(fileArg, 'utf8').trim()
  : args.includes('--stdin') ? readFileSync(0, 'utf8').trim()
    : args.filter((_, i) => !consumed.has(i)).join(' ').trim();

if (!conv || (!text && !upload && images.length === 0)) {
  console.error('Usage: send.js --conv <g…|u…> [--thread <id>] [--at <qq>]… [--image <url|path>]… ("text" | --file <p> | --stdin) | --upload <path>');
  process.exit(1);
}

const CAP = Number(process.env.APP_SEND_CAP_PER_HOUR || 30);
const TIMES = './.send-times.json';
let times = []; try { times = JSON.parse(readFileSync(TIMES, 'utf8')); } catch {}
const now = Date.now();
times = times.filter((t) => t > now - 3600_000);
if (times.length >= CAP) { console.error(`FAIL send cap reached (${CAP}/hour) — runaway guard; wait or raise send_cap_per_hour`); process.exit(1); }

try {
  const c = parseConv(conv);
  const me = await call('get_login_info');
  if (upload) {
    const p = resolve(upload);
    if (statSync(p).size > 20 * 1024 * 1024) throw new Error(`${basename(p)} is over 20 MB`);
    const file = `base64://${readFileSync(p).toString('base64')}`;
    if (c.kind === 'group') await call('upload_group_file', { group_id: c.id, file, name: basename(p) });
    else await call('upload_private_file', { user_id: c.id, file, name: basename(p) });
    console.log(`uploaded -> conv ${conv} file ${basename(p)}`);
  } else {
    const message = [];
    if (thread) message.push({ type: 'reply', data: { id: String(thread) } });
    for (const q of ats) message.push({ type: 'at', data: { qq: String(q) } }, { type: 'text', data: { text: ' ' } });
    if (text) message.push({ type: 'text', data: { text } });
    for (const img of images) message.push({ type: 'image', data: { file: /^https?:\/\//.test(img) ? img : `base64://${readFileSync(resolve(img)).toString('base64')}` } });
    const r = c.kind === 'group'
      ? await call('send_group_msg', { group_id: c.id, message })
      : await call('send_private_msg', { user_id: c.id, message });
    const id = String(r.message_id);
    record({
      ts: Math.floor(now / 1000), id, conv, user: String(me.user_id), name: me.nickname, self: true, reply_to: thread,
      text: [ats.map((q) => `@${q}`).join(' '), text, ...images.map((i) => `[图片 ${i}]`)].filter(Boolean).join(' '), files: [],
    });
    console.log(`sent -> conv ${conv} ts ${id}`);
  }
  times.push(now); writeFileSync(TIMES, JSON.stringify(times));
} catch (e) {
  console.error('FAIL', e.message);
  process.exit(1);
}
