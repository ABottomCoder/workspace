// Contract verb: validate-creds. Checks the OneBot endpoint and that the account is in every
// listened group; prints "<nickname> <qq> in <group names>" and exits 0, or the error and exits 1.
import { call, list } from './onebot.mjs';

try {
  const me = await call('get_login_info');
  const groups = await call('get_group_list');
  const byConv = new Map((groups || []).map((g) => [`g${g.group_id}`, g.group_name]));
  const convs = list(process.env.APP_LISTEN_CONVS).filter((c) => c.startsWith('g'));
  const missing = convs.filter((c) => !byConv.has(c));
  if (missing.length) { console.error(`account ${me.user_id} is not in ${missing.join(', ')}`); process.exit(1); }
  console.log(`${me.nickname} ${me.user_id} in ${convs.length ? convs.map((c) => byConv.get(c)).join(', ') : `${byConv.size} group(s)`}`);
} catch (e) {
  console.error(`OneBot rejected or unreachable (${e.message}) — is the protocol endpoint running and logged in?`);
  process.exit(1);
}
