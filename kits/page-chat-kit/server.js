'use strict';
/**
 * page-chat-kit — reusable page-mounted chat bot.
 *
 * Serves:
 *   /_portal/*          login / chat API / SSE / static (the kit's own namespace)
 *   /                   portal shell (login-gated): folded launcher + chat panel,
 *                       and — if FRONT_TARGET is set — an iframe wrapping your site
 *   everything else     (only if FRONT_TARGET set) reverse-proxied to your site, login-gated
 *
 * The "agent" (AGENT_USER) is a special account that: receives every message over SSE,
 * sees all private threads, and posts replies via reply.js / POST /_portal/api/chat/reply
 * (authenticated with AGENT_KEY). Point any backend session at the events log + reply API.
 *
 * Zero coupling to the wrapped site: separate dir / port / sqlite db; the site is only proxied.
 */
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const express = require('express');
const cookieSession = require('cookie-session');
const Database = require('better-sqlite3');
const httpProxy = require('http-proxy');
const multer = require('multer');

// ---- minimal .env loader ----
(() => {
  const envPath = path.join(__dirname, '.env');
  if (!fs.existsSync(envPath)) return;
  for (const line of fs.readFileSync(envPath, 'utf8').split('\n')) {
    const m = line.match(/^\s*([A-Z0-9_]+)\s*=\s*(.*)\s*$/);
    if (m && !(m[1] in process.env)) process.env[m[1]] = m[2].replace(/^["']|["']$/g, '');
  }
})();

const PORT = parseInt(process.env.PORT || '8790', 10);
const SESSION_SECRET = process.env.SESSION_SECRET || crypto.randomBytes(32).toString('hex');
const AGENT_KEY = process.env.AGENT_KEY || 'change-this-agent-key';
const AGENT_USER = process.env.AGENT_USER || 'agent'; // the account that receives all + replies
const BRAND = process.env.BRAND || 'Chat Portal';
const FRONT_TARGET = (process.env.FRONT_TARGET || '').trim(); // optional: wrap an existing site
const FRAME_PATH = process.env.FRAME_PATH || '/';
const FRAME_ENABLED = !!FRONT_TARGET;
const SESSION_MAX_AGE_MS = parseInt(process.env.SESSION_MAX_AGE_MS || String(24 * 3600 * 1000), 10);

const ACCOUNTS = JSON.parse(fs.readFileSync(path.join(__dirname, 'accounts.json'), 'utf8'));
const ACCT = Object.fromEntries(ACCOUNTS.map((a) => [a.user, a]));
const labelOf = (u) => (ACCT[u] ? ACCT[u].label : u);
const agentLabel = () => labelOf(AGENT_USER);

// resolve @label / @username inside content → set of hit usernames
function parseMentions(content) {
  if (!content) return [];
  const hit = new Set();
  for (const a of ACCOUNTS) {
    if (content.includes('@' + a.label) || content.includes('@' + a.user)) hit.add(a.user);
  }
  return [...hit];
}

// ---- outbound DLP (optional): scrub agent replies before they reach users ----
// last-resort machine backstop; your first line is the agent's own judgment.
const AI_VENDOR_RE = [
  /claude/i, /anthropic/i, /\bgpt(-?\d+)?\b/i, /openai/i, /\bopus\b/i, /\bsonnet\b/i,
  /\bhaiku\b/i, /gemini/i, /llama/i, /mistral/i, /\bllm\b/i, /大语言模型/,
  /system\s*-?\s*prompt/i, /系统提示词/,
];
const dlpPatterns = [];
if (process.env.DLP_HIDE_AI_VENDORS === '1') dlpPatterns.push(...AI_VENDOR_RE);
for (const s of (process.env.DLP_EXTRA || '').split(',').map((x) => x.trim()).filter(Boolean)) {
  try { dlpPatterns.push(new RegExp(s, 'i')); } catch { dlpPatterns.push(s); }
}
const SECRET_VALUES = [AGENT_KEY, SESSION_SECRET].filter((v) => v && v.length >= 12);
function scrubSensitive(text) {
  if (!text) return null;
  for (const v of SECRET_VALUES) if (text.includes(v)) return 'secret';
  for (const p of dlpPatterns) {
    if (p instanceof RegExp) { const m = text.match(p); if (m) return m[0]; }
    else if (text.includes(p)) return p;
  }
  return null; // null = clean
}

// ---- uploads (direct, size-limited) ----
const MAX_UPLOAD_MB = parseInt(process.env.MAX_UPLOAD_MB || '50', 10);
const UPLOAD_DIR = path.join(__dirname, 'uploads');
if (!fs.existsSync(UPLOAD_DIR)) fs.mkdirSync(UPLOAD_DIR, { recursive: true });
const ALLOWED_EXT = new Set(['png', 'jpg', 'jpeg', 'gif', 'webp', 'svg', 'pdf',
  'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 'zip', 'txt', 'csv', 'md', 'json',
  'mp4', 'mov', 'webm', 'mp3', 'wav', 'm4a']);
const fixName = (n) => Buffer.from(n || 'file', 'latin1').toString('utf8'); // multer defaults latin1; fix unicode names
const extOf = (n) => (path.extname(n || '') || '').toLowerCase().replace('.', '');
const uploadMw = multer({
  storage: multer.diskStorage({
    destination: (req, file, cb) => cb(null, UPLOAD_DIR),
    filename: (req, file, cb) => cb(null,
      Date.now() + '-' + crypto.randomBytes(6).toString('hex') + '.' + (extOf(file.originalname) || 'bin')),
  }),
  limits: { fileSize: MAX_UPLOAD_MB * 1024 * 1024, files: 1 },
  fileFilter: (req, file, cb) => cb(null, ALLOWED_EXT.has(extOf(fixName(file.originalname)))),
}).single('file');

// ---- sqlite ----
const db = new Database(path.join(__dirname, 'chat.db'));
db.pragma('journal_mode = WAL');
db.exec(`
  CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    scope TEXT NOT NULL, thread_user TEXT NOT NULL, sender TEXT NOT NULL,
    role TEXT NOT NULL, content TEXT NOT NULL, attachment TEXT, mentions TEXT,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
    status TEXT NOT NULL DEFAULT 'pending'
  );
  CREATE INDEX IF NOT EXISTS idx_thread ON messages(scope, thread_user, id);
`);

// events log — the agent tails this to receive user messages
const EVENTS_LOG = path.join(__dirname, 'chat-events.log');
function logEvent(msg) {
  const att = msg.attachment ? JSON.parse(msg.attachment) : null;
  const mentions = msg.mentions ? JSON.parse(msg.mentions) : null;
  fs.appendFile(EVENTS_LOG, '[chat-event] ' + JSON.stringify({
    id: msg.id, scope: msg.scope, thread_user: msg.thread_user,
    sender: msg.sender, label: labelOf(msg.sender), content: msg.content, ts: msg.created_at,
    attachment: att ? { name: att.name, size: att.size, mime: att.mime, file: att.stored } : null,
    mentions, mentions_me: !!(mentions && mentions.includes(AGENT_USER)),
  }) + '\n', () => {});
}

const clients = [];
function pushToClients(msg) {
  const payload = 'data: ' + JSON.stringify({
    id: msg.id, scope: msg.scope, thread_user: msg.thread_user, sender: msg.sender,
    label: labelOf(msg.sender), role: msg.role, content: msg.content, ts: msg.created_at,
    attachment: msg.attachment ? JSON.parse(msg.attachment) : null,
    mentions: msg.mentions ? JSON.parse(msg.mentions) : null,
  }) + '\n\n';
  for (const c of clients) {
    if (msg.scope === 'group' || c.user === msg.thread_user || c.user === AGENT_USER) c.res.write(payload);
  }
}
function insertMessage({ scope, thread_user, sender, role, content, attachment, mentions }) {
  const mArr = scope === 'group' && mentions && mentions.length ? mentions : null;
  const info = db.prepare(`INSERT INTO messages (scope,thread_user,sender,role,content,attachment,mentions) VALUES (?,?,?,?,?,?,?)`)
    .run(scope, thread_user, sender, role, content, attachment ? JSON.stringify(attachment) : null, mArr ? JSON.stringify(mArr) : null);
  const msg = db.prepare(`SELECT * FROM messages WHERE id=?`).get(info.lastInsertRowid);
  pushToClients(msg);
  if (role === 'user') logEvent(msg);
  return msg;
}

// ---- app ----
const app = express();
app.set('trust proxy', true);

const portalJson = express.json({ limit: '256kb' });
const session = cookieSession({
  name: 'pck_sess', secret: SESSION_SECRET, httpOnly: true, sameSite: 'lax',
  secure: process.env.COOKIE_SECURE === '1', maxAge: SESSION_MAX_AGE_MS,
});
app.use(session);

function authed(req) { return req.session && req.session.user && ACCT[req.session.user]; }
function requireAuthApi(req, res, next) { return authed(req) ? next() : res.status(401).json({ error: 'unauthorized' }); }

// ============ portal routes (/_portal/*) ============
const P = express.Router();
P.use(portalJson);
// `code` on every error is a stable machine key the UI localizes; `error` stays the English fallback.
P.get('/api/config', (req, res) => res.json({ brand: BRAND, agentUser: AGENT_USER, agentLabel: agentLabel(), frameEnabled: FRAME_ENABLED, maxUploadMb: MAX_UPLOAD_MB }));
P.post('/api/login', (req, res) => {
  const { user, password } = req.body || {};
  // Username is case-insensitive + whitespace-trimmed (users type "ken"/" Ken");
  // resolve to the canonical account so downstream exact ACCT lookups stay valid.
  const key = typeof user === 'string' ? user.trim().toLowerCase() : '';
  const a = ACCOUNTS.find((x) => x.user.toLowerCase() === key);
  if (!a || a.password !== password) return res.status(401).json({ error: 'Wrong username or password', code: 'bad_credentials' });
  req.session.user = a.user;
  res.json({ ok: true, user: a.user, label: a.label, role: a.role });
});
P.post('/api/logout', (req, res) => { req.session = null; res.json({ ok: true }); });
P.get('/api/me', requireAuthApi, (req, res) => {
  const a = ACCT[req.session.user]; res.json({ user: a.user, label: a.label, role: a.role });
});
// change own password: verify current, atomic write-back to accounts.json
P.post('/api/change-password', requireAuthApi, (req, res) => {
  const a = ACCT[req.session.user];
  const current = (req.body && req.body.current) || '';
  const next = (req.body && req.body.next) || '';
  if (!a || a.password !== current) return res.status(400).json({ error: 'Current password is incorrect', code: 'bad_current' });
  if (typeof next !== 'string' || next.length < 6) return res.status(400).json({ error: 'New password must be at least 6 characters', code: 'pwd_short' });
  if (next.length > 64) return res.status(400).json({ error: 'New password too long', code: 'pwd_long' });
  if (next === current) return res.status(400).json({ error: 'New password must differ from current', code: 'pwd_same' });
  a.password = next; // same object ref as in ACCOUNTS; in-memory effective immediately
  const tmp = path.join(__dirname, 'accounts.json.tmp');
  fs.writeFileSync(tmp, JSON.stringify(ACCOUNTS, null, 2));
  fs.renameSync(tmp, path.join(__dirname, 'accounts.json')); // atomic replace
  res.json({ ok: true });
});
P.get('/api/frame', requireAuthApi, (req, res) => res.json({ enabled: FRAME_ENABLED, path: FRAME_PATH }));
P.get('/api/roster', requireAuthApi, (req, res) =>
  res.json(ACCOUNTS.map((a) => ({ user: a.user, label: a.label, role: a.role }))));
P.get('/api/chat/history', requireAuthApi, (req, res) => {
  const scope = req.query.scope === 'group' ? 'group' : 'private';
  const thread_user = scope === 'group' ? 'group' : req.session.user;
  const limit = Math.min(Math.max(parseInt(req.query.limit, 10) || 30, 1), 100);
  const before = parseInt(req.query.before, 10) || 0;
  const rows = (before > 0
    ? db.prepare(`SELECT id,scope,thread_user,sender,role,content,created_at,attachment,mentions
        FROM messages WHERE scope=? AND thread_user=? AND id<? ORDER BY id DESC LIMIT ?`).all(scope, thread_user, before, limit)
    : db.prepare(`SELECT id,scope,thread_user,sender,role,content,created_at,attachment,mentions
        FROM messages WHERE scope=? AND thread_user=? ORDER BY id DESC LIMIT ?`).all(scope, thread_user, limit)
  ).reverse(); // newest batch, returned oldest→newest
  res.json(rows.map((r) => ({ ...r, label: labelOf(r.sender),
    attachment: r.attachment ? JSON.parse(r.attachment) : null,
    mentions: r.mentions ? JSON.parse(r.mentions) : null })));
});
P.post('/api/chat/send', requireAuthApi, (req, res) => {
  const user = req.session.user;
  const scope = req.body && req.body.scope === 'group' ? 'group' : 'private';
  const content = ((req.body && req.body.content) || '').toString().trim();
  if (!content) return res.status(400).json({ error: 'Empty content', code: 'empty' });
  if (content.length > 8000) return res.status(400).json({ error: 'Content too long', code: 'content_long' });
  const thread_user = scope === 'group' ? 'group' : user;
  const msg = insertMessage({ scope, thread_user, sender: user, role: 'user', content, mentions: parseMentions(content) });
  res.json({ ok: true, id: msg.id });
});
P.post('/api/chat/upload', requireAuthApi, (req, res) => {
  uploadMw(req, res, (err) => {
    if (err) return res.status(400).json(err.code === 'LIMIT_FILE_SIZE'
      ? { error: `File exceeds ${MAX_UPLOAD_MB}MB limit`, code: 'file_too_large' }
      : { error: 'Upload failed', code: 'upload_failed' });
    if (!req.file) return res.status(400).json({ error: 'Unsupported file type or no file selected', code: 'file_type' });
    const user = req.session.user;
    const scope = req.body && req.body.scope === 'group' ? 'group' : 'private';
    const thread_user = scope === 'group' ? 'group' : user;
    const caption = ((req.body && req.body.content) || '').toString().trim().slice(0, 2000);
    const attachment = { name: fixName(req.file.originalname), size: req.file.size,
      mime: req.file.mimetype, stored: req.file.filename, ext: extOf(req.file.filename) };
    const msg = insertMessage({ scope, thread_user, sender: user, role: 'user', content: caption, attachment });
    res.json({ ok: true, id: msg.id, attachment });
  });
});
// download/view attachment (auth, by message id)
P.get('/api/chat/file/:id', requireAuthApi, (req, res) => {
  const row = db.prepare(`SELECT scope,thread_user,attachment FROM messages WHERE id=?`).get(parseInt(req.params.id, 10));
  if (!row || !row.attachment) return res.status(404).end();
  if (row.scope === 'private' && req.session.user !== row.thread_user && req.session.user !== AGENT_USER) return res.status(403).end();
  const att = JSON.parse(row.attachment);
  const fp = path.join(UPLOAD_DIR, path.basename(att.stored || ''));
  if (!fp.startsWith(UPLOAD_DIR) || !fs.existsSync(fp)) return res.status(404).end();
  const inline = /^(png|jpe?g|gif|webp|svg|pdf|mp4|webm|mov|mp3|wav|m4a)$/i.test(att.ext || '');
  res.setHeader('Content-Disposition', `${inline ? 'inline' : 'attachment'}; filename*=UTF-8''${encodeURIComponent(att.name)}`);
  res.sendFile(fp);
});
// agent posts a reply (AGENT_KEY header, or an authed agent session)
function agentAuthed(req) { return req.get('X-Agent-Key') === AGENT_KEY || (req.session && req.session.user === AGENT_USER); }
P.post('/api/chat/reply', portalJson, (req, res) => {
  if (!agentAuthed(req)) return res.status(401).json({ error: 'unauthorized' });
  const b = req.body || {};
  const scope = b.scope === 'group' ? 'group' : 'private';
  const content = (b.content || '').toString().trim();
  if (!content) return res.status(400).json({ error: 'Empty content' });
  const bad = scrubSensitive(content);
  if (bad) { fs.appendFile(path.join(__dirname, 'dlp-blocks.log'), new Date().toISOString() + ` DLP[${scope}] hit "${bad}": ` + content.slice(0, 140) + '\n', () => {}); return res.status(422).json({ error: 'blocked_sensitive', term: bad }); }
  const thread_user = scope === 'group' ? 'group' : (b.thread_user || '').toString();
  if (scope === 'private' && !ACCT[thread_user]) return res.status(400).json({ error: 'Unknown private thread user' });
  const msg = insertMessage({ scope, thread_user, sender: AGENT_USER, role: 'assistant', content, mentions: parseMentions(content) });
  db.prepare(`UPDATE messages SET status='answered' WHERE scope=? AND thread_user=? AND role='user' AND status='pending'`)
    .run(scope, thread_user);
  res.json({ ok: true, id: msg.id });
});
// agent posts a message with an attachment copied from a local file path
P.post('/api/chat/reply-file', portalJson, (req, res) => {
  if (!agentAuthed(req)) return res.status(401).json({ error: 'unauthorized' });
  const b = req.body || {};
  const scope = b.scope === 'group' ? 'group' : 'private';
  const thread_user = scope === 'group' ? 'group' : (b.thread_user || '').toString();
  if (scope === 'private' && !ACCT[thread_user]) return res.status(400).json({ error: 'Unknown private thread user' });
  const srcPath = (b.path || '').toString();
  if (!srcPath || !fs.existsSync(srcPath)) return res.status(400).json({ error: 'File not found: ' + srcPath });
  const st = fs.statSync(srcPath);
  if (st.size > MAX_UPLOAD_MB * 1024 * 1024) return res.status(400).json({ error: `File exceeds ${MAX_UPLOAD_MB}MB` });
  const orig = path.basename(srcPath);
  const ext = extOf(orig) || 'bin';
  const stored = Date.now() + '-' + crypto.randomBytes(6).toString('hex') + '.' + ext;
  fs.copyFileSync(srcPath, path.join(UPLOAD_DIR, stored));
  const attachment = { name: orig, size: st.size, mime: '', stored, ext };
  const caption = (b.content || '').toString().trim().slice(0, 2000);
  const bad = scrubSensitive(caption + ' ' + orig);
  if (bad) return res.status(422).json({ error: 'blocked_sensitive', term: bad });
  const msg = insertMessage({ scope, thread_user, sender: AGENT_USER, role: 'assistant', content: caption, attachment, mentions: parseMentions(caption) });
  res.json({ ok: true, id: msg.id, attachment });
});
P.get('/api/chat/stream', requireAuthApi, (req, res) => {
  res.set({ 'Content-Type': 'text/event-stream', 'Cache-Control': 'no-cache', Connection: 'keep-alive' });
  res.flushHeaders(); res.write('retry: 3000\n\n');
  const client = { user: req.session.user, res };
  clients.push(client);
  const ping = setInterval(() => res.write(': ping\n\n'), 25000);
  req.on('close', () => { clearInterval(ping); const i = clients.indexOf(client); if (i >= 0) clients.splice(i, 1); });
});
P.get('/login', (req, res) => res.sendFile(path.join(__dirname, 'public', 'login.html')));
P.use('/static', express.static(path.join(__dirname, 'public')));
app.use('/_portal', P);

// ============ portal shell `/` ============
app.get('/', (req, res) => {
  if (!authed(req)) return res.redirect('/_portal/login');
  res.sendFile(path.join(__dirname, 'public', 'app.html'));
});

// ============ OPTIONAL: reverse-proxy the rest to your site (login-gated) ============
if (FRAME_ENABLED) {
  const proxy = httpProxy.createProxyServer({ target: FRONT_TARGET, changeOrigin: false, ws: true });
  proxy.on('proxyRes', (proxyRes) => {
    // allow same-origin iframe embedding: drop X-Frame-Options, relax CSP frame-ancestors
    delete proxyRes.headers['x-frame-options'];
    const csp = proxyRes.headers['content-security-policy'];
    if (csp) proxyRes.headers['content-security-policy'] =
      csp.replace(/frame-ancestors[^;]*;?/gi, "frame-ancestors 'self';");
  });
  proxy.on('error', (err, req, res) => {
    if (res && res.writeHead) { res.writeHead(502, { 'Content-Type': 'text/plain; charset=utf-8' });
      res.end('Wrapped site temporarily unavailable (FRONT_TARGET not running)'); }
  });
  app.use((req, res) => {
    if (!authed(req)) {
      if (req.method === 'GET' && req.accepts('html')) return res.redirect('/_portal/login');
      return res.status(401).end();
    }
    proxy.web(req, res);
  });
  const server = app.listen(PORT, '0.0.0.0', () =>
    console.log(`page-chat-kit on http://0.0.0.0:${PORT}  agent=${AGENT_USER}  proxy→${FRONT_TARGET}`));
  server.on('upgrade', (req, socket, head) => proxy.ws(req, socket, head)); // wrapped site ws
} else {
  app.listen(PORT, '0.0.0.0', () =>
    console.log(`page-chat-kit on http://0.0.0.0:${PORT}  agent=${AGENT_USER}  (standalone, no site wrapping)`));
}
