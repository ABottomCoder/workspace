// Fill the open "Generate an app-level token" modal (Basic Information page): name +
// connections:write scope + Generate, then read back the xapp- token.
// Usage: node gen-token.mjs [--name socket] [--out token-file]
import { connect, takeOpt, usage, emitToken } from './lib.mjs';

let args = process.argv.slice(2);
usage('usage: node gen-token.mjs [--name socket] [--out token-file]   (open the token modal first)', args);
let name, out;
[name, args] = takeOpt(args, '--name');
[out, args] = takeOpt(args, '--out');

const { browser, page, shot } = await connect();
try {
  const nameField = page.locator('input[placeholder*="refer to your token" i]');
  await nameField.click();
  await nameField.fill(name || 'socket');
  await page.waitForTimeout(400);
  await page.getByRole('button', { name: /^Add Scope$/i }).click();
  await page.waitForTimeout(1000);
  await shot('gt-1-addscope');
  await page.getByText(/connections:write/i).first().click();
  await page.waitForTimeout(800);
  await shot('gt-2-scope-picked');
  await page.getByRole('button', { name: /^Generate$/i }).click();
  await page.waitForTimeout(2500);
  // no screenshot after this point: the token is visible on screen
  let token = null;
  for (const el of await page.locator('input, code, pre, [class*="token" i]').all()) {
    const v = (await el.inputValue().catch(() => null)) || (await el.textContent().catch(() => ''));
    if (v && v.trim().startsWith('xapp-')) { token = v.trim(); break; }
  }
  if (!emitToken('XAPP_TOKEN', token, out)) process.exitCode = 3;
} catch (e) {
  console.error('FAILED:', e.message.split('\n')[0]);
  await shot('gt-ERROR');
  process.exitCode = 2;
} finally { await browser.close(); }
