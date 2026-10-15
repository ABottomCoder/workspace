// Flexible single-step driver: perform a sequence of simple actions, then screenshot.
// Usage: node step.mjs <shotname> <action> [action...]
//   actions:  click=<text>     (first element containing text; buttons/links/options preferred)
//             clickrole=<role>:<name-regex>
//             type=<text>      (keyboard.insertText into focused element)
//             selectall        (Cmd+A on macOS, Ctrl+A elsewhere)  |  del (Backspace)  |  press=<Key>
//             file=<path>      (insertText with the file's content)
//             goto=<url>       |  wait=<ms>
import { readFileSync } from 'node:fs';
import { connect, usage } from './lib.mjs';

usage('usage: node step.mjs <shotname> <action> [action...]  (see header comment for actions)', process.argv.slice(2));
const [,, shotName, ...actions] = process.argv;
if (!shotName) { console.error('usage: node step.mjs <shotname> <action> [action...]'); process.exit(1); }
const { browser, page, shot } = await connect();

try {
  for (const a of actions) {
    const [cmd, ...rest] = a.split('=');
    const val = rest.join('=');
    if (cmd === 'goto') await page.goto(val, { waitUntil: 'domcontentloaded' });
    else if (cmd === 'wait') await page.waitForTimeout(Number(val));
    else if (cmd === 'click') {
      const byRole = page.getByRole('button', { name: new RegExp(val, 'i') })
        .or(page.getByRole('link', { name: new RegExp(val, 'i') }))
        .or(page.getByRole('option', { name: new RegExp(val, 'i') }))
        .or(page.getByRole('tab', { name: new RegExp(val, 'i') }));
      if (await byRole.count()) await byRole.first().click({ timeout: 8000 });
      else await page.getByText(new RegExp(val, 'i')).first().click({ timeout: 8000 });
      await page.waitForTimeout(900);
    }
    else if (cmd === 'clickrole') { const [role, name] = val.split(':'); await page.getByRole(role, { name: new RegExp(name, 'i') }).first().click({ timeout: 8000 }); await page.waitForTimeout(900); }
    else if (cmd === 'type') { await page.keyboard.insertText(val); await page.waitForTimeout(300); }
    else if (cmd === 'file') { await page.keyboard.insertText(readFileSync(val, 'utf8')); await page.waitForTimeout(500); }
    else if (cmd === 'selectall') await page.keyboard.press(process.platform === 'darwin' ? 'Meta+A' : 'Control+A');
    else if (cmd === 'del') await page.keyboard.press('Backspace');
    else if (cmd === 'press') await page.keyboard.press(val);
  }
  await page.waitForTimeout(600);
  console.log('URL:', page.url());
} catch (e) {
  console.error('STEP-FAILED:', e.message.split('\n')[0]);
  process.exitCode = 2;
} finally {
  await shot(shotName);
  await browser.close();
}
