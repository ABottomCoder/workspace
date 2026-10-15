// Navigate the attached Chrome tab (or stay), print URL + title, screenshot.
// Usage: node nav.mjs <url|stay> [shot-name]
import { connect, usage } from './lib.mjs';

const args = process.argv.slice(2);
usage('usage: node nav.mjs <url|stay> [shot-name]', args);
const [target, name] = args;
const { browser, page, shot } = await connect();
try {
  if (target && target !== 'stay') {
    await page.goto(target, { waitUntil: 'domcontentloaded', timeout: 30000 });
    await page.waitForTimeout(2500);
  }
  console.log('URL:', page.url());
  console.log('TITLE:', await page.title());
  await shot(name || 'shot');
} finally { await browser.close(); }
