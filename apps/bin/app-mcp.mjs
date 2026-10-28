// MCP server (stdio) that gives a RESTRICTED app session its only way to the chat: wait for the
// next event, read a conversation, send. Channel-agnostic: it calls the channel verbs
// (apps/channels/<kind>/) and wait-event.sh exactly as an unrestricted session would via Bash.
// Started by persona-session.sh through --mcp-config; env: APP_REF (<co>/<id>), APP_RUN, APP_CHANNEL.
// Memory catch-up: on each wait_event, if a past day (last 7) has a transcript but no digest, it
// starts `persona-session.sh --digest` for the oldest such day in the background (one at a time).
// So digests happen while the app runs, with no scheduler (launchd can't read ~/Documents anyway).
import { spawn } from 'node:child_process';
import { existsSync, openSync, readFileSync, realpathSync, statSync, unlinkSync, writeFileSync } from 'node:fs';
import { dirname, join, sep } from 'node:path';
import { fileURLToPath } from 'node:url';
import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { z } from 'zod';

const BIN = dirname(fileURLToPath(import.meta.url));
const { APP_REF, APP_RUN, APP_CHANNEL } = process.env;
if (!APP_REF || !APP_RUN || !APP_CHANNEL) { console.error('app-mcp: APP_REF, APP_RUN, APP_CHANNEL required'); process.exit(1); }

function verb(name) {
  const d = join(BIN, '..', 'channels', APP_CHANNEL);
  for (const ext of ['.js', '.mjs']) if (existsSync(join(d, name + ext))) return [process.execPath, join(d, name + ext)];
  if (existsSync(join(d, name + '.sh'))) return ['bash', join(d, name + '.sh')];
  throw new Error(`channel ${APP_CHANNEL} has no '${name}'`);
}
// Run a command without a shell (arguments never pass through one); resolve {code, out, err}.
function run(cmd, args, { stdin, timeoutMs, cwd = APP_RUN } = {}) {
  return new Promise((resolve) => {
    const p = spawn(cmd, args, { cwd, stdio: ['pipe', 'pipe', 'pipe'] });
    let out = '', err = '', timedOut = false;
    p.stdout.on('data', (d) => { out += d; });
    p.stderr.on('data', (d) => { err += d; });
    const t = timeoutMs ? setTimeout(() => { timedOut = true; p.kill('SIGTERM'); }, timeoutMs) : null;
    p.on('close', (code) => { if (t) clearTimeout(t); resolve({ code, out, err, timedOut }); });
    if (stdin != null) p.stdin.end(stdin); else p.stdin.end();
  });
}
const text = (s) => ({ content: [{ type: 'text', text: s }] });
const readSince = async (conv, peek) => {
  const [c, ...a] = verb('read-since');
  const r = await run(c, [...a, conv, ...(peek ? ['--peek'] : [])]);
  return (r.out + (r.code ? `\n(read failed: ${r.err.trim()})` : '')).trim();
};

const MEM = join(APP_RUN, '..', 'memory');
const LOCK = join(APP_RUN, 'digest.pid');
const ymd = (d) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
function maybeDigest() {
  try {
    if (!existsSync(join(MEM, 'raw'))) return;
    if (existsSync(LOCK)) { try { process.kill(Number(readFileSync(LOCK, 'utf8')), 0); return; } catch { /* stale lock */ } }
    for (let i = 7; i >= 1; i--) {
      const d = ymd(new Date(Date.now() - i * 86400_000));
      if (!existsSync(join(MEM, 'raw', `${d}.jsonl`)) || existsSync(join(MEM, 'days', `${d}.md`))) continue;
      const env = { ...process.env }; delete env.CLAUDECODE;   // a fresh, separate claude run
      const log = openSync(join(APP_RUN, 'digest.log'), 'a');
      const p = spawn('bash', [join(BIN, 'persona-session.sh'), '--digest', APP_REF, d], { detached: true, stdio: ['ignore', log, log], env });
      writeFileSync(LOCK, String(p.pid)); p.unref();
      return;
    }
  } catch (e) { console.error('[digest]', e.message); }
}

const server = new McpServer({ name: 'app', version: '0.1.0' });

server.registerTool('wait_event', {
  title: 'Wait for the next chat event',
  description: 'Blocks until someone writes in a listened conversation (one event per burst of messages), then returns '
    + 'the event and every new message in that conversation since you last read it. Returns "no event" after max_wait_s; '
    + 'then call it again. Call it again right after handling each event — it is how you stay present in the chat.',
  inputSchema: { max_wait_s: z.number().int().min(30).max(840).default(840).describe('Seconds to wait before returning "no event".') },
}, async ({ max_wait_s }) => {
  // One wait at a time: two wait-event.sh runs share one offset and would deliver an event twice.
  // Claude Code may move this long call to the background: the session is then woken when it
  // returns, and the Stop hook lets the session idle while WAITING exists (persona-stop-hook.sh).
  if (waiting) return text('wait_event is already running in the background. End your turn now, silently; you will be woken when it returns.');
  waiting = true; writeFileSync(WAITING, String(process.pid));
  try { return await waitOnce(max_wait_s); } finally { waiting = false; try { unlinkSync(WAITING); } catch {} }
});
let waiting = false;
const WAITING = join(APP_RUN, 'session', 'waiting');
async function waitOnce(max_wait_s) {
  maybeDigest();
  const r = await run('bash', [join(BIN, 'wait-event.sh'), APP_REF], { timeoutMs: max_wait_s * 1000 });
  if (r.timedOut) return text(`no event in ${max_wait_s}s — call wait_event again.`);
  const lines = r.out.split('\n').filter((l) => /^\[(chat|slack)-event\] /.test(l));
  if (r.code === 3) return text(`WARNING: the listener was not receiving (${r.out.trim()}). Messages from that gap may be missing.\nCall wait_event again.`);
  // Recycle catch-up (wait-event.sh peeks, never advances): read for real here, or the same rows
  // come back on every recycle.
  const caught = [...r.out.matchAll(/^\[catchup (\S+) /gm)].map((m) => m[1]);
  if (!lines.length && caught.length) {
    const parts = [];
    for (const conv of new Set(caught)) parts.push(`CATCH-UP conv=${conv} (written while the listener reconnected)\nNEW MESSAGES:\n${await readSince(conv, false)}`);
    return text(parts.join('\n\n'));
  }
  if (!lines.length) return text(`no event (${(r.out + r.err).trim().slice(0, 300) || `exit ${r.code}`}) — call wait_event again.`);
  const parts = [];
  for (const conv of new Set(lines.map((l) => { try { return JSON.parse(l.replace(/^\[\w+-event\] /, '')).conv; } catch { return null; } }).filter(Boolean))) {
    const ev = JSON.parse(lines.filter((l) => l.includes(`"conv":"${conv}"`)).pop().replace(/^\[\w+-event\] /, ''));
    parts.push(`EVENT conv=${conv} type=${ev.type}${ev.burst ? ` burst=${ev.burst}` : ''}${ev.mentioned ? ' (you were addressed)' : ''}${ev.followup ? ' (includes someone you answered a few minutes ago: judge from the content whether it is for you)' : ''} last_message_id=${ev.ts}\n`
      + `NEW MESSAGES:\n${await readSince(conv, false)}`);
  }
  return text(parts.join('\n\n'));
}

server.registerTool('read', {
  title: 'Read a conversation',
  description: 'New messages in a conversation since your last read (advances the read cursor unless peek).',
  inputSchema: { conv: z.string().describe('Conversation id from an event, e.g. g123456.'), peek: z.boolean().default(false) },
}, async ({ conv, peek }) => text(await readSince(conv, peek) || '(nothing)'));

server.registerTool('history', {
  title: 'Recent history of a conversation',
  description: 'The last n messages of a conversation from the transcript, regardless of what you have read. Use it at session start and when you need more context than the new messages.',
  inputSchema: { conv: z.string().describe('Conversation id, e.g. g123456.'), n: z.number().int().min(1).max(300).default(80) },
}, async ({ conv, n }) => {
  const [c, ...a] = verb('read-since');
  const r = await run(c, [...a, conv, '--last', String(n)]);
  return text(r.code === 0 ? r.out.trim() : `FAILED: ${(r.err || r.out).trim()}`);
});

server.registerTool('send', {
  title: 'Send a message',
  description: 'Post a message in a conversation as yourself. Optionally quote-reply a message, @ people, or attach images by URL.',
  inputSchema: {
    conv: z.string().describe('Conversation id from the event.'),
    text: z.string().default('').describe('Message text. Plain text, no markdown.'),
    reply_to: z.string().optional().describe('Message id (#id in the transcript) to quote-reply.'),
    at: z.array(z.string()).default([]).describe('User ids to @.'),
    images: z.array(z.string().url().regex(/^https:\/\//, 'https only')).max(4).default([]).describe('Image URLs (https only) to attach.'),
  },
}, async ({ conv, text: body, reply_to, at, images }) => {
  if (!body && !images.length) return text('nothing to send');
  const [c, ...a] = verb('send');
  const args = [...a, '--conv', conv, ...(reply_to ? ['--thread', reply_to] : []), ...at.flatMap((q) => ['--at', q]),
    ...images.flatMap((u) => ['--image', u]), ...(body ? ['--stdin'] : [])];
  const r = await run(c, args, { stdin: body || null, timeoutMs: 30_000 });
  return text(r.code === 0 ? r.out.trim() : `FAILED: ${(r.err || r.out).trim()}`);
});

// Files: only from <memory dir>/outbox/, which the session writes itself. Transcripts, profiles and
// notes stay unsendable even if someone talks the session into trying.
const OUTBOX = join(MEM, 'outbox');
server.registerTool('send_file', {
  title: 'Send a file',
  description: 'Send a file you wrote into outbox/ (in your memory dir) to a conversation, as a file, or as an image if as_image is true.',
  inputSchema: {
    conv: z.string().describe('Conversation id from the event.'),
    path: z.string().describe('File name or path inside outbox/, e.g. "teams.txt".'),
    as_image: z.boolean().default(false).describe('Send an image file inline as a picture instead of as a file.'),
  },
}, async ({ conv, path, as_image }) => {
  let real;
  try { real = realpathSync(join(OUTBOX, path.replace(/^outbox\//, ''))); } catch { return text(`FAILED: no such file in outbox/: ${path}`); }
  if (!real.startsWith(realpathSync(OUTBOX) + sep)) return text('FAILED: only files inside outbox/ can be sent');
  if (!statSync(real).isFile()) return text('FAILED: not a file');
  const [c, ...a] = verb('send');
  const r = await run(c, [...a, '--conv', conv, ...(as_image ? ['--image', real] : ['--upload', real])], { timeoutMs: 120_000 });
  return text(r.code === 0 ? r.out.trim() : `FAILED: ${(r.err || r.out).trim()}`);
});

await server.connect(new StdioServerTransport());
