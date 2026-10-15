/* page-chat-kit UI strings — shared by login.html and app.html.
 *
 * To add a language: copy the `en` block, give it a new key (e.g. `fr`), set `_name`
 * (shown on the language switch) and `_htmlLang`, and translate the values.
 * Missing keys fall back to English. `{agent}`, `{brand}`, `{mb}`, `{name}` are placeholders.
 * Language = the visitor's saved choice, else PCK_DEFAULT_LANG.
 */
const PCK_DEFAULT_LANG = 'en';
const PCK_STRINGS = {
  en: {
    _name: 'English', _htmlLang: 'en',
    loginSub: 'Please sign in', loginUser: 'Username', loginPwd: 'Password', loginSignin: 'Sign in',
    loginBad: 'Wrong username or password', loginFail: 'Sign-in failed', loginFill: 'Please enter your username and password',
    menuChat: 'Chat with {agent}', menuGroup: 'Group chat',
    menuPwd: 'Change password', menuLogout: 'Sign out',
    fabOpen: 'Open menu', fabClose: 'Collapse', close: 'Close',
    titlePrivate: 'Chat with {agent}', titleGroup: 'Group chat',
    members: 'Members', membersHd: 'Members · click a name to @', membersNone: 'No matching members',
    attach: 'Attach file (≤{mb}MB)', inputPh: 'Type a message, Enter to send…', send: 'Send',
    empty: 'No messages yet — say hi!', atme: '@me',
    roleApprover: 'Approver', roleTeam: 'Team',
    pwdTitle: 'Change password', pwdAccount: 'Account: {name}', pwdCur: 'Current password',
    pwdNew: 'New password (min 6 chars)', pwdNew2: 'Confirm new password',
    cancel: 'Cancel', save: 'Save',
    pwdFill: 'Please fill in all fields', pwdMismatch: 'Passwords do not match',
    pwdOk: '✓ Password changed — use it next time', pwdFail: 'Change failed',
    logoutConfirm: 'Sign out of {brand}?', logoutFail: 'Sign-out failed — please retry',
    sessionExpired: 'Your session has expired — please sign in again',
    sendFail: 'Failed to send — your message was restored, please retry',
    netErr: 'Network error — please retry',
    errBadCurrent: 'Current password is incorrect', errPwdShort: 'New password must be at least 6 characters',
    errPwdLong: 'New password is too long', errPwdSame: 'New password must differ from the current one',
    errEmpty: 'Message is empty', errContentLong: 'Message is too long (8000 chars max)',
    errFileLarge: 'File exceeds the {mb}MB limit — use another method for large files',
    errFileType: 'Unsupported file type', errUploadFailed: 'Upload failed',
  },
  zh: {
    _name: '中文', _htmlLang: 'zh-CN',
    loginSub: '请登录', loginUser: '用户名', loginPwd: '密码', loginSignin: '登录',
    loginBad: '用户名或密码错误', loginFail: '登录失败', loginFill: '请输入用户名和密码',
    menuChat: '与 {agent} 私聊', menuGroup: '群聊',
    menuPwd: '修改密码', menuLogout: '退出登录',
    fabOpen: '展开菜单', fabClose: '收起', close: '关闭',
    titlePrivate: '与 {agent} 私聊', titleGroup: '群聊',
    members: '群成员', membersHd: '群成员 · 点名字即可 @', membersNone: '没有匹配的成员',
    attach: '发送文件（≤{mb}MB）', inputPh: '输入消息，回车发送…', send: '发送',
    empty: '还没有消息，打个招呼吧！', atme: '@我',
    roleApprover: '审批人', roleTeam: '团队',
    pwdTitle: '修改密码', pwdAccount: '账号：{name}', pwdCur: '当前密码',
    pwdNew: '新密码（至少 6 位）', pwdNew2: '确认新密码',
    cancel: '取消', save: '保存',
    pwdFill: '请填写所有字段', pwdMismatch: '两次输入的新密码不一致',
    pwdOk: '✓ 密码已修改，下次用新密码登录', pwdFail: '修改失败',
    logoutConfirm: '确定退出 {brand} 吗？', logoutFail: '退出失败，请重试',
    sessionExpired: '登录已过期，请重新登录',
    sendFail: '发送失败——消息已保留在输入框，请重试',
    netErr: '网络错误，请重试',
    errBadCurrent: '当前密码不正确', errPwdShort: '新密码至少 6 位',
    errPwdLong: '新密码过长', errPwdSame: '新密码不能与当前密码相同',
    errEmpty: '消息内容为空', errContentLong: '消息过长（最多 8000 字）',
    errFileLarge: '文件超过 {mb}MB 限制——大文件请走其他方式',
    errFileType: '不支持的文件类型', errUploadFailed: '上传失败',
  },
};

let LANG = (() => { try { return localStorage.getItem('pck_lang'); } catch (e) { return null; } })() || PCK_DEFAULT_LANG;
if (!PCK_STRINGS[LANG]) LANG = 'en';

function pckFormat(key, vars) {
  const dict = PCK_STRINGS[LANG] || PCK_STRINGS.en;
  const s = dict[key] != null ? dict[key] : (PCK_STRINGS.en[key] != null ? PCK_STRINGS.en[key] : key);
  return String(s).replace(/\{(\w+)\}/g, (m, k) => (vars && vars[k] != null ? vars[k] : m));
}
function pckNextLang() {
  const langs = Object.keys(PCK_STRINGS);
  return langs[(langs.indexOf(LANG) + 1) % langs.length];
}
function pckCycleLang() {
  LANG = pckNextLang();
  try { localStorage.setItem('pck_lang', LANG); } catch (e) { /* private mode */ }
}
/* Static text carries data-i18n / data-i18n-title / data-i18n-ph; [data-i18n-next-lang] shows the next language's name. */
function pckApplyStatic(t) {
  document.documentElement.lang = (PCK_STRINGS[LANG] || PCK_STRINGS.en)._htmlLang;
  document.querySelectorAll('[data-i18n]').forEach((el) => { el.textContent = t(el.dataset.i18n); });
  document.querySelectorAll('[data-i18n-title]').forEach((el) => { el.title = t(el.dataset.i18nTitle); });
  document.querySelectorAll('[data-i18n-ph]').forEach((el) => { el.placeholder = t(el.dataset.i18nPh); });
  document.querySelectorAll('[data-i18n-next-lang]').forEach((el) => { el.textContent = PCK_STRINGS[pckNextLang()]._name; });
}
