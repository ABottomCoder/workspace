// Shared helpers: attach to an already-running, logged-in Chrome over CDP.
import { chromium } from 'playwright-core';
import { mkdirSync, writeFileSync } from 'node:fs';
import { resolve } from 'node:path';

export const CDP_URL = process.env.CDP_URL || 'http://localhost:9222';
export const SHOTS = resolve(process.env.SLACKAUTO_SHOTS || 'shots');

export async function connect() {
  mkdirSync(SHOTS, { recursive: true });
  const browser = await chromium.connectOverCDP(CDP_URL);
  const ctx = browser.contexts()[0];
  const page = ctx.pages()[0] || await ctx.newPage();
  const shot = (name) => page.screenshot({ path: `${SHOTS}/${name}.png` });
  return { browser, page, shot };
}

// Pull "--name value" out of argv; returns [value|undefined, remaining args].
export function takeOpt(args, name) {
  const i = args.indexOf(name);
  if (i < 0) return [undefined, args];
  return [args[i + 1], args.filter((_, j) => j !== i && j !== i + 1)];
}

// A token goes to a 0600 file when --out is given; otherwise to stdout with a warning.
export function emitToken(label, token, outFile) {
  if (!token) { console.log(`${label}: NOT-FOUND (see screenshots in ${SHOTS})`); return false; }
  if (outFile) {
    writeFileSync(outFile, token + '\n', { mode: 0o600 });
    console.log(`${label}: written to ${outFile} (${token.slice(0, 9)}…)`);
  } else {
    console.error('warning: printing a secret to stdout; pass --out <file> to write it to a 0600 file instead');
    console.log(`${label}: ${token}`);
  }
  return true;
}

export function usage(text, args) {
  if (args.includes('--help') || args.includes('-h')) { console.log(text); process.exit(0); }
}
