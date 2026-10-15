#!/usr/bin/env node
'use strict';
/**
 * Agent reply script — post a message as the agent (AGENT_USER).
 *   node reply.js --private <user> "text"
 *   node reply.js --group "text"
 * Authenticated with X-Agent-Key; writes via POST /_portal/api/chat/reply.
 * The server sets sender = AGENT_USER and pushes to browsers over SSE in realtime.
 *
 * To send a file:  POST /_portal/api/chat/reply-file  { scope, thread_user, path, content }
 */
const fs = require('fs'); const path = require('path');
(() => { const p = path.join(__dirname, '.env'); if (!fs.existsSync(p)) return;
  for (const l of fs.readFileSync(p, 'utf8').split('\n')) { const m = l.match(/^\s*([A-Z0-9_]+)\s*=\s*(.*)\s*$/);
    if (m && !(m[1] in process.env)) process.env[m[1]] = m[2].replace(/^["']|["']$/g, ''); } })();

const PORT = process.env.PORT || '8790';
const KEY = process.env.AGENT_KEY;
const args = process.argv.slice(2);
let scope = 'private', thread_user = null, content = null;
for (let i = 0; i < args.length; i++) {
  if (args[i] === '--group') scope = 'group';
  else if (args[i] === '--private') { scope = 'private'; thread_user = args[++i]; }
  else content = args[i];
}
if (!content || (scope === 'private' && !thread_user)) {
  console.error('usage: node reply.js --private <user> "text"  |  node reply.js --group "text"');
  process.exit(1);
}
fetch(`http://0.0.0.0:${PORT}/_portal/api/chat/reply`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json', 'X-Agent-Key': KEY },
  body: JSON.stringify({ scope, thread_user, content }),
}).then(async (r) => {
  const j = await r.json().catch(() => ({}));
  if (r.ok) console.log(`sent -> ${scope}${thread_user ? '/' + thread_user : ''} id ${j.id}`);
  else { console.error('FAIL', r.status, j); process.exit(1); }
}).catch((e) => { console.error('ERR', e.message); process.exit(1); });
