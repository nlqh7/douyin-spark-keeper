const elements = {
  scan: document.querySelector('#scan'),
  login: document.querySelector('#login'),
  loginStatus: document.querySelector('#login-status'),
  toggle: document.querySelector('#auto-toggle'),
  watchingBadge: document.querySelector('#watching-badge'),
  autoDescription: document.querySelector('#auto-description'),
  nextRun: document.querySelector('#next-run'),
  scheduleTime: document.querySelector('#schedule-time'),
  scheduleSummary: document.querySelector('#schedule-summary'),
  accountName: document.querySelector('#account-name'),
  grayCount: document.querySelector('#gray-count'),
  grayNames: document.querySelector('#gray-names'),
  dialog: document.querySelector('#confirm-dialog'),
  confirmDescription: document.querySelector('#confirm-description'),
  cancelWatch: document.querySelector('#cancel-watch'),
  confirmWatch: document.querySelector('#confirm-watch'),
  logs: document.querySelector('#logs'),
  logsView: document.querySelector('#logs-view'),
  overviewView: document.querySelector('#overview-view'),
  pageTitle: document.querySelector('#page-title'),
  pageSection: document.querySelector('#page-section'),
  form: document.querySelector('#settings-form'),
  timeInput: document.querySelector('#time-input'),
  browserMode: document.querySelector('#browser-mode'),
  messageInput: document.querySelector('#message-input'),
  stickerInput: document.querySelector('#sticker-input'),
  textField: document.querySelector('#text-field'),
  stickerField: document.querySelector('#sticker-field'),
  stickerCurrent: document.querySelector('#sticker-current'),
  stickerCurrentImage: document.querySelector('#sticker-current-image'),
  stickerCurrentName: document.querySelector('#sticker-current-name'),
  stickerOptions: document.querySelector('#sticker-options'),
  saveSettings: document.querySelector('#save-settings'),
  settingsStatus: document.querySelector('#settings-status'),
  toast: document.querySelector('#toast'),
  announcement: document.querySelector('#announcement'),
};

let busy = false;
let loggedIn = false;
let settingsLoaded = false;
let toastTimer;
let currentConfig = { time: '23:00', message_type: 'text', content: '火', browser_mode: 'isolated' };
const STICKERS = ['续火花', '晚上好', '比心', '早上好', '早点睡', '在干嘛', '开心', '嗨', '爱心', '绝了', '笑死', '已阅'];

function friendlyError(error) {
  const message = error?.message || '操作失败';
  return message.replace(/^Error invoking remote method '[^']+': (?:Error: )?/, '').replace(/^错误:\s*/, '');
}

function notify(message) {
  clearTimeout(toastTimer);
  elements.toast.textContent = message;
  elements.toast.hidden = false;
  elements.announcement.textContent = message;
  toastTimer = setTimeout(() => { elements.toast.hidden = true; }, 4200);
}

function updateControls() {
  elements.scan.disabled = busy || !loggedIn || !settingsLoaded;
  elements.login.disabled = busy || !settingsLoaded;
  elements.toggle.disabled = busy || !loggedIn || !settingsLoaded;
  elements.saveSettings.disabled = busy || !settingsLoaded;
  elements.login.className = `button ${loggedIn ? 'secondary' : 'primary'}`;
  elements.scan.className = `button ${loggedIn ? 'primary' : 'secondary'}`;
}

function updateNextRun() {
  const now = new Date();
  const [hour, minute] = currentConfig.time.split(':').map(Number);
  const target = new Date(now);
  target.setHours(hour, minute, 0, 0);
  elements.nextRun.textContent = now < target ? '今天' : '明天';
}

function renderAccount(state) {
  elements.accountName.textContent = state.account?.name || '未登录';
  elements.grayCount.textContent = state.scan?.count ?? '—';
  elements.grayNames.replaceChildren();
  const targets = state.scan?.targets || [];
  if (!targets.length) {
    elements.grayNames.textContent = state.scan?.count === 0 ? '没有待续火花' : '还没有扫描记录';
    return;
  }
  for (const name of targets) {
    const item = document.createElement('span');
    item.textContent = name;
    elements.grayNames.append(item);
  }
}

function selectedMessageType() {
  return document.querySelector('input[name="message-type"]:checked').value;
}

function updateMessageFields() {
  const isText = selectedMessageType() === 'text';
  elements.textField.hidden = !isText;
  elements.stickerField.hidden = isText;
  elements.messageInput.required = isText;
}

function updateStickerCurrent() {
  const name = elements.stickerInput.value;
  elements.stickerCurrentImage.src = `../../assets/stickers/${name}.png`;
  elements.stickerCurrentName.textContent = name;
  elements.stickerOptions.querySelectorAll('button').forEach((button) => {
    const selected = button.dataset.name === name;
    button.classList.toggle('selected', selected);
    button.setAttribute('aria-pressed', String(selected));
  });
}

function renderStickerOptions() {
  for (const name of STICKERS) {
    const button = document.createElement('button');
    button.type = 'button';
    button.dataset.name = name;
    button.setAttribute('aria-pressed', 'false');
    const image = document.createElement('img');
    image.src = `../../assets/stickers/${name}.png`;
    image.alt = '';
    const label = document.createElement('span');
    label.textContent = name;
    button.append(image, label);
    button.addEventListener('click', () => {
      elements.stickerInput.value = name;
      elements.stickerOptions.hidden = true;
      elements.stickerCurrent.setAttribute('aria-expanded', 'false');
      updateStickerCurrent();
    });
    elements.stickerOptions.append(button);
  }
  updateStickerCurrent();
}

function renderConfig() {
  elements.scheduleTime.textContent = currentConfig.time;
  const kind = currentConfig.message_type === 'sticker' ? '原生表情' : '「' + currentConfig.content + '」';
  elements.scheduleSummary.textContent = `所有灰色火花，各发一个${kind}`;
  elements.timeInput.value = currentConfig.time;
  elements.browserMode.value = currentConfig.browser_mode;
  document.querySelector(`input[name="message-type"][value="${currentConfig.message_type}"]`).checked = true;
  if (currentConfig.message_type === 'sticker') elements.stickerInput.value = currentConfig.content;
  else elements.messageInput.value = currentConfig.content;
  updateMessageFields();
  updateStickerCurrent();
  updateNextRun();
}

async function refresh(syncSettings = false) {
  try {
    const state = await window.spark.status();
    renderAccount(state);
    loggedIn = state.loggedIn;
    elements.loginStatus.textContent = state.config.browser_mode === 'webbridge' ? 'WebBridge 已连接' : (state.config.browser_mode === 'default' ? '默认 Chrome' : (loggedIn ? '已登录' : '需要登录'));
    elements.loginStatus.classList.toggle('ready', loggedIn);
    elements.toggle.checked = state.enabled || state.watching;
    elements.watchingBadge.hidden = !state.watching;
    elements.autoDescription.textContent = state.watching ? '监视中，保持应用开启' : '保持应用和电脑运行';
    if (syncSettings) {
      currentConfig = state.config;
      renderConfig();
      settingsLoaded = true;
    }
  } catch (error) {
    elements.loginStatus.textContent = '状态异常';
    notify(friendlyError(error));
  } finally {
    updateControls();
  }
}

async function refreshLogs() {
  elements.logs.textContent = await window.spark.logs();
}

function showView(view) {
  const isLogs = view === 'logs';
  elements.overviewView.hidden = isLogs;
  elements.logsView.hidden = !isLogs;
  elements.pageTitle.textContent = isLogs ? '运行记录' : '每日续火';
  elements.pageSection.textContent = isLogs ? '记录' : '续火';
  document.querySelectorAll('[data-view]').forEach((button) => button.classList.toggle('active', button.dataset.view === view));
  if (isLogs) refreshLogs().catch((error) => notify(friendlyError(error)));
}

async function perform(action, successMessage, label) {
  if (busy) return;
  busy = true;
  updateControls();
  const button = label === 'login' ? elements.login : elements.scan;
  const previousText = button.textContent;
  if (label === 'login') button.textContent = '等待扫码…';
  if (label === 'scan') button.querySelector('span').textContent = '正在扫描…';
  try {
    const result = await action();
    if (result?.output) elements.logs.textContent = result.output;
    notify(successMessage);
  } catch (error) {
    notify(friendlyError(error));
  } finally {
    if (label === 'login') button.textContent = previousText;
    if (label === 'scan') button.querySelector('span').textContent = '扫描火花';
    busy = false;
    await refresh();
  }
}

elements.scan.addEventListener('click', () => perform(() => window.spark.dryRun(), '扫描完成，未发送任何消息', 'scan'));
elements.login.addEventListener('click', () => perform(() => window.spark.login(), '登录状态已保存', 'login'));
document.querySelectorAll('[data-view]').forEach((button) => button.addEventListener('click', () => showView(button.dataset.view)));
document.querySelectorAll('input[name="message-type"]').forEach((input) => input.addEventListener('change', updateMessageFields));
document.querySelectorAll('[data-content]').forEach((button) => button.addEventListener('click', () => {
  elements.messageInput.value = button.dataset.content;
  elements.messageInput.focus();
}));
elements.stickerCurrent.addEventListener('click', () => {
  elements.stickerOptions.hidden = !elements.stickerOptions.hidden;
  elements.stickerCurrent.setAttribute('aria-expanded', String(!elements.stickerOptions.hidden));
});
document.addEventListener('click', (event) => {
  if (!event.target.closest('.sticker-picker')) {
    elements.stickerOptions.hidden = true;
    elements.stickerCurrent.setAttribute('aria-expanded', 'false');
  }
});

elements.form.addEventListener('submit', async (event) => {
  event.preventDefault();
  if (busy) return;
  const messageType = selectedMessageType();
  const settings = {
    time: elements.timeInput.value,
    messageType,
    content: messageType === 'sticker' ? elements.stickerInput.value : elements.messageInput.value,
    browserMode: elements.browserMode.value,
  };
  busy = true;
  updateControls();
  elements.settingsStatus.textContent = '';
  try {
    await window.spark.saveConfig(settings);
    currentConfig = { time: settings.time, message_type: messageType, content: settings.content.trim(), browser_mode: settings.browserMode };
    renderConfig();
    elements.settingsStatus.textContent = '已保存';
    notify('发送设置已保存');
  } catch (error) {
    notify(friendlyError(error));
  } finally {
    busy = false;
    updateControls();
  }
});

elements.toggle.addEventListener('change', () => {
  if (!elements.toggle.checked) {
    perform(() => window.spark.pause(), '自动续火已暂停', 'pause');
    return;
  }
  elements.confirmDescription.textContent = `每天 ${currentConfig.time}，所有灰色火花都会收到“${currentConfig.content}”。请保持应用和电脑运行。`;
  elements.dialog.showModal();
});
elements.cancelWatch.addEventListener('click', () => {
  elements.dialog.close();
  elements.toggle.checked = false;
});
elements.confirmWatch.addEventListener('click', async () => {
  elements.dialog.close();
  await perform(() => window.spark.startWatch(true), '自动续火已开启', 'watch');
});
elements.dialog.addEventListener('cancel', () => { elements.toggle.checked = false; });
window.spark.onLog((message) => {
  elements.logs.textContent += `${elements.logs.textContent ? '\n' : ''}${message.trimEnd()}`;
});

renderStickerOptions();
refresh(true);
