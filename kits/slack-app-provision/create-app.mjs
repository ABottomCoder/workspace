// Create one Slack app from a manifest via the api.slack.com UI (Socket Mode bot by default).
// Usage: node create-app.mjs <AppName> <displayname> <workspace-name-regex> [--manifest file.json]
import { readFileSync } from 'node:fs';
import { connect, takeOpt, usage } from './lib.mjs';

let args = process.argv.slice(2);
usage('usage: node create-app.mjs <AppName> <displayname> <workspace-name-regex> [--manifest file.json] [--dry-run]', args);
let manifestFile;
[manifestFile, args] = takeOpt(args, '--manifest');
const dryRun = args.includes('--dry-run');   // stop at the review step, create nothing
args = args.filter((a) => a !== '--dry-run');
const [appName, displayName, workspace] = args;
if (!appName || !displayName || !workspace) {
  console.error('usage: node create-app.mjs <AppName> <displayname> <workspace-name-regex> [--manifest file.json] [--dry-run]');
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

  const cookies = page.getByRole('button', { name: /reject all cookies/i });   // banner can cover the modal
  if (await cookies.count()) await cookies.first().click().catch(() => {});

  await page.getByText(/from a manifest/i).first().click();
  await page.waitForTimeout(800);
  // Current UI: pick "From a manifest", then Continue
  const cont = page.getByRole('button', { name: /^continue$/i });
  if (await cont.count()) { await cont.first().click(); await page.waitForTimeout(1500); }
  await shot('2-after-pick');

  // Current UI shows the manifest editor and the workspace picker on one step;
  // the older UI asked for the workspace first, then showed the editor after Next.
  const editor = page.locator('.cm-content, .CodeMirror, [class*="codemirror" i], textarea, [contenteditable="true"]').first();
  if (await editor.count()) {
    await fillManifest();
    await pickWorkspace();
  } else {
    await pickWorkspace();
    await page.getByRole('button', { name: /^next$/i }).first().click();
    await page.waitForTimeout(1500);
    await fillManifest();
  }
  await shot('5-manifest-and-workspace');

  async function pickWorkspace() {
    const native = page.locator('[role="dialog"] select').first();
    if (await native.count()) {
      const val = await native.locator('option', { hasText: wsRe }).first().getAttribute('value');
      if (val) await native.selectOption(val);
    } else {
      await page.getByText(/select a workspace/i).first().click();
      await page.waitForTimeout(800);
      await page.getByText(wsRe).last().click();   // last: the open menu sits above the app list in the DOM order
    }
    await page.waitForTimeout(800);
  }

  async function fillManifest() {
    const jsonTab = page.getByRole('tab', { name: /json/i }).or(page.getByText(/^json$/i));
    if (await jsonTab.count()) { await jsonTab.first().click(); await page.waitForTimeout(600); }
    await editor.click();
    await page.keyboard.press(process.platform === 'darwin' ? 'Meta+A' : 'Control+A');
    await page.keyboard.press('Backspace');
    await page.keyboard.insertText(manifest);
    await page.waitForTimeout(800);
  }

  await page.getByRole('button', { name: /^next$/i }).first().click();
  await page.waitForTimeout(1800);
  await shot('6-review');

  if (dryRun) {
    console.log('DRY-RUN: reached the review step; closing without creating');
    await page.keyboard.press('Escape');
  } else {
    await page.getByRole('button', { name: /^create$/i }).first().click();
    await page.waitForTimeout(4000);
    await shot('7-created');
    console.log('FINAL-URL:', page.url());   // contains the new app id: /apps/<APP_ID>/...
    console.log('TITLE:', await page.title());
  }
} catch (e) {
  await shot('ERROR');
  console.error('STEP-FAILED:', e.message.split('\n')[0]);
  console.log('FINAL-URL:', page.url());
  process.exitCode = 2;
} finally {
  await browser.close();   // detaches from Chrome; does not close it
}
