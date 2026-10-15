#!/usr/bin/env node
/**
 * mcp-scaffold — minimal remote MCP server (Streamable HTTP transport) with bearer-token auth.
 *
 * Tool: `echo(input) -> "echo: <input>"`. Replace it with your own tools in buildServer().
 *
 * Run:   MCP_AUTH_TOKEN=<random> PORT=5400 npm start
 * Wire:  claude mcp add --transport http --header "Authorization: Bearer <token>" my-tools http://0.0.0.0:5400/mcp
 */

import express from 'express';
import { randomUUID, timingSafeEqual } from 'node:crypto';
import { readFileSync } from 'node:fs';
import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { StreamableHTTPServerTransport } from '@modelcontextprotocol/sdk/server/streamableHttp.js';
import { z } from 'zod';

// Lightweight .env loader (avoids a dotenv dependency)
try {
  const envFile = readFileSync(new URL('./.env', import.meta.url), 'utf8');
  for (const line of envFile.split('\n')) {
    const m = line.match(/^\s*([A-Z_][A-Z0-9_]*)\s*=\s*(.*)\s*$/);
    if (m && !process.env[m[1]]) process.env[m[1]] = m[2];
  }
} catch { /* no .env, OK */ }

if (process.argv.includes('--help') || process.argv.includes('-h')) {
  console.log('usage: MCP_AUTH_TOKEN=<token> [PORT=5400] [HOST=0.0.0.0] node index.js');
  process.exit(0);
}

const PORT = Number(process.env.PORT) || 5400;
const HOST = process.env.HOST || '0.0.0.0';
const AUTH_TOKEN = process.env.MCP_AUTH_TOKEN || '';
if (AUTH_TOKEN.length < 16) {
  console.error('[mcp] MCP_AUTH_TOKEN must be set (16+ chars), e.g. `openssl rand -hex 32`');
  process.exit(1);
}

function buildServer() {
  const server = new McpServer({ name: 'mcp-scaffold', version: '0.1.0' });

  server.registerTool(
    'echo',
    {
      title: 'Echo',
      description: 'Returns the input string unchanged. Placeholder tool; replace with your own.',
      inputSchema: { input: z.string().describe('Any string. Will be echoed back verbatim.') },
    },
    async ({ input }) => ({ content: [{ type: 'text', text: `echo: ${input}` }] }),
  );

  return server;
}

// Bearer-token check for every /mcp request (constant-time compare).
const expected = Buffer.from(`Bearer ${AUTH_TOKEN}`);
function requireBearer(req, res, next) {
  const got = Buffer.from(req.get('authorization') || '');
  if (got.length === expected.length && timingSafeEqual(got, expected)) return next();
  res.status(401).set('WWW-Authenticate', 'Bearer').json({
    jsonrpc: '2.0', error: { code: -32001, message: 'Unauthorized' }, id: null,
  });
}

const app = express();
app.use(express.json());
app.use('/mcp', requireBearer);

// Session-aware transport: the first request (`initialize`) creates a session; later
// requests reuse it via the Mcp-Session-Id header. Serves many concurrent clients.
const sessions = new Map();

app.post('/mcp', async (req, res) => {
  const sessionId = req.headers['mcp-session-id'];
  let transport;

  if (sessionId && sessions.has(sessionId)) {
    transport = sessions.get(sessionId);
  } else if (!sessionId && req.body?.method === 'initialize') {
    transport = new StreamableHTTPServerTransport({
      sessionIdGenerator: () => randomUUID(),
      onsessioninitialized: (id) => {
        sessions.set(id, transport);
        console.log('[mcp] session initialized:', id);
      },
    });
    transport.onclose = () => {
      if (transport.sessionId) {
        sessions.delete(transport.sessionId);
        console.log('[mcp] session closed:', transport.sessionId);
      }
    };
    await buildServer().connect(transport);
  } else {
    res.status(400).json({
      jsonrpc: '2.0',
      error: { code: -32000, message: 'Bad Request: no session and not an initialize' },
      id: null,
    });
    return;
  }

  await transport.handleRequest(req, res, req.body);
});

const sessionRequest = async (req, res) => {
  const sessionId = req.headers['mcp-session-id'];
  if (!sessionId || !sessions.has(sessionId)) {
    res.status(400).send('Missing or invalid session');
    return;
  }
  await sessions.get(sessionId).handleRequest(req, res);
};
app.get('/mcp', sessionRequest);    // server-to-client SSE stream
app.delete('/mcp', sessionRequest); // session termination

app.get('/health', (_req, res) => res.json({ ok: true, sessions: sessions.size }));

app.listen(PORT, HOST, () => {
  console.log(`[mcp] listening on http://${HOST}:${PORT}/mcp (health: /health)`);
});
