// Create one Slack app from a manifest via the api.slack.com UI (Socket Mode bot by default).
// Usage: node create-app.mjs <AppName> <displayname> <workspace-name-regex> [--manifest file.json]
import { readFileSync } from 'node:fs';
import { connect, takeOpt, usage } from './lib.mjs';

let args = process.argv.slice(2);
usage('usage: node create-app.mjs <AppName> <displayname> <workspace-name-regex> [--manifest file.json]', args);
let manifestFile;
[manifestFile, args] = takeOpt(args, '--manifest');
const [appName, displayName, workspace] = args;
if (!appName || !displayName || !workspace) {
  console.error('usage: node create-app.mjs <AppName> <displayname> <workspace-name-regex> [--manifest file.json]');
  process.exit(1);
}
const wsRe = new RegExp(workspace, 'i');

const manifest = manifestFile ? readFileSync(manifestFile, 'utf8') : JSON.stringify({
  display_information: { name: appName, description: 'Event-driven assistant: forwards @mentions and DMs to an agent session', background_color: '#1a1a2e' },
  features: { bot_user: { display_name: displayName, always_online: true } },
  oauth_config: { scopes: { bot: ['app_mentions:read', 'chat:write', 'im:history', 'im:read', 'im:write', 'channels:history', 'groups:history', 'users:read', 'channels:read'] } },
  settings: { event_subscriptions: { bot_events: ['app_mention', 'message.im'] }, interactivity: { is_enabled: false }, socket_mode_enabled: true, org_deploy_enabled: false, token_rotation_enabled: false },
}, null, 2);

const { browser, page, shot: rawShot } = await connect();
const shot = (n) => rawShot(`${appName}-${n}`);

try {
  await page.goto('https://api.slack.com/apps', { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(2000);
  await page.getByRole('button', { name: /create new app/i }).or(page.getByRole('link', { name: /create new app/i })).first().click();
  await page.waitForTimeout(1500);
  await shot('1-create-modal');

  await page.getByText(/from a manifest/i).first().click();
  await page.waitForTimeout(1500);
  await shot('2-workspace-pick');

  // Workspace selector: native <select> or a custom combobox
  const wsDropdown = page.locator('select, [role="combobox"], [data-qa*="workspace"], button:has-text("Select a workspace")').first();
  if (await wsDropdown.count()) {
    const tag = await wsDropdown.evaluate((el) => el.tagName.toLowerCase());
    if (tag === 'select') {
      const val = await wsDropdown.locator('option', { hasText: wsRe }).first().getAttribute('value');
      if (val) await wsDropdown.selectOption(val);
    } else {
      await wsDropdown.click();
      await page.waitForTimeout(800);
      await page.getByText(wsRe).first().click();
    }
  }
  await page.waitForTimeout(800);
  await shot('3-workspace-selected');
  await page.getByRole('button', { name: /^next$/i }).first().click();
  await page.waitForTimeout(1500);
  await shot('4-manifest-editor');

  const jsonTab = page.getByRole('tab', { name: /json/i }).or(page.getByText(/^json$/i));
  if (await jsonTab.count()) { await jsonTab.first().click(); await page.waitForTimeout(600); }

  // Replace the code editor's content with the manifest
  const editor = page.locator('.CodeMirror, [class*="codemirror" i], textarea, [contenteditable="true"]').first();
  await editor.click();
  await page.keyboard.press(process.platform === 'darwin' ? 'Meta+A' : 'Control+A');
  await page.keyboard.press('Backspace');
  await page.keyboard.insertText(manifest);
  await page.waitForTimeout(800);
  await shot('5-manifest-pasted');

  await page.getByRole('button', { name: /^next$/i }).first().click();
  await page.waitForTimeout(1800);
  await shot('6-review');

  await page.getByRole('button', { name: /^create$/i }).first().click();
  await page.waitForTimeout(4000);
  await shot('7-created');
  console.log('FINAL-URL:', page.url());   // contains the new app id: /apps/<APP_ID>/...
  console.log('TITLE:', await page.title());
} catch (e) {
  await shot('ERROR');
  console.error('STEP-FAILED:', e.message.split('\n')[0]);
  console.log('FINAL-URL:', page.url());
  process.exitCode = 2;
} finally {
  await browser.close();   // detaches from Chrome; does not close it
}
