#!/usr/bin/env node
// Every hex colour in a deployed site's JS bundle, scored as if it were text on a background.
//
// Why read the bundle: grepping source for literal hex values misses colours passed
// through constants, props or colour maps; scanning rendered pages misses any state the
// crawl never entered. The built bundle has resolved the source, and a colour does not
// need to be on screen to appear in it.
//
// Output is CANDIDATES, not defects: the script cannot know which background a colour is
// used against, or whether it is text at all. A failing hex may be a border, icon, chart
// series or fill.
//
// Usage: node contrast-check.mjs <url> [--bg #ffffff] [--min 1.8] [--max 4.5] [--top 30]

const args = process.argv.slice(2);
const opt = (name, dflt) => { const i = args.indexOf(name); return i >= 0 ? args[i + 1] : dflt; };
const url = args.find((a, i) => !a.startsWith('--') && !(i > 0 && args[i - 1].startsWith('--')));
if (!url || args.includes('--help') || args.includes('-h')) {
  console.log('usage: node contrast-check.mjs <url> [--bg #ffffff] [--min 1.8] [--max 4.5] [--top 30]');
  console.log('  Lists hex colours in the page\'s same-origin JS bundles whose contrast against --bg');
  console.log('  is in [min, max): dark enough to plausibly be text, yet below WCAG AA (4.5:1).');
  process.exit(args.includes('--help') || args.includes('-h') ? 0 : 1);
}
const BG = opt('--bg', '#ffffff').toLowerCase();
const MIN = Number(opt('--min', '1.8'));   // below ~1.8:1 a colour is almost surely a fill or hairline
const MAX = Number(opt('--max', '4.5'));   // WCAG AA for body text
const TOP = Number(opt('--top', '30'));
if (!/^#[0-9a-f]{6}$/.test(BG)) { console.error('--bg must be #rrggbb'); process.exit(1); }

const base = new URL(url);
const html = await (await fetch(base)).text();
const srcs = [...html.matchAll(/<script[^>]*\ssrc=["']([^"']+\.m?js[^"']*)["']/gi)]
  .map((m) => new URL(m[1], base))
  .filter((u) => u.origin === base.origin);
if (!srcs.length) { console.error('no same-origin <script src> found in', url); process.exit(1); }

let js = '';
for (const u of srcs) js += await (await fetch(u)).text();

const hex = (h) => [1, 3, 5].map((i) => parseInt(h.slice(i, i + 2), 16));
const lin = (c) => { c /= 255; return c <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4); };
const L = (h) => { const [r, g, b] = hex(h); return 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b); };
const ratio = (a, b) => { const l1 = L(a), l2 = L(b); return (Math.max(l1, l2) + 0.05) / (Math.min(l1, l2) + 0.05); };

const counts = new Map();
for (const raw of js.match(/#[0-9a-fA-F]{6}\b/g) || []) {
  const h = raw.toLowerCase();
  counts.set(h, (counts.get(h) || 0) + 1);
}
// A long list of obvious fills is one nobody reads; keep the band that is plausibly text.
const rows = [...counts].map(([h, n]) => ({ h, n, r: +ratio(h, BG).toFixed(2) }))
  .filter((x) => x.r < MAX && x.r >= MIN && x.h !== BG)
  .sort((a, b) => b.n - a.n);

console.log(`${srcs.length} bundle(s): ${srcs.map((u) => u.pathname).join(', ')}; ${counts.size} distinct hex colours`);
console.log(`${rows.length} in the ${MIN}–${MAX}:1 band against ${BG}: plausibly text, would fail.`);
console.log('CANDIDATES, not defects: a hex here may be a border, icon, chart series or fill.\n');
for (const x of rows.slice(0, TOP)) console.log(`  ${x.h}  ${String(x.n).padStart(4)}×   ${x.r.toFixed(2)}:1`);
if (rows.length > TOP) console.log(`  … and ${rows.length - TOP} more`);
