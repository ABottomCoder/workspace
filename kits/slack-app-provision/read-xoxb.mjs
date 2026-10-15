// Read an installed app's bot token (xoxb-) from its OAuth & Permissions page.
// Usage: node read-xoxb.mjs <APP_ID> [--out token-file]
import { connect, takeOpt, usage, emitToken } from './lib.mjs';

let args = process.argv.slice(2);
usage('usage: node read-xoxb.mjs <APP_ID> [--out token-file]   (install the app to the workspace first)', args);
let out;
[out, args] = takeOpt(args, '--out');
const appId = args[0];
if (!appId) { console.error('usage: node read-xoxb.mjs <APP_ID> [--out token-file]'); process.exit(1); }

const { browser, page } = await connect();
try {
  await page.goto(`https://api.slack.com/apps/${encodeURIComponent(appId)}/oauth`, { waitUntil: 'domcontentloaded' });
  let token = null;
  for (let i = 0; i < 4 && !token; i++) {   // the token field renders late
    await page.waitForTimeout(1500);
    const vals = await page.evaluate(() => [...document.querySelectorAll('input, code, pre')]
      .map((el) => (el.value || el.textContent || '').trim()));
    token = vals.find((v) => v.startsWith('xoxb-')) || null;
  }
  if (!emitToken('XOXB_TOKEN', token, out)) process.exitCode = 3;
} catch (e) { console.error('FAILED:', e.message.split('\n')[0]); process.exitCode = 2; }
finally { await browser.close(); }
