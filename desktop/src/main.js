const { app, BrowserWindow, ipcMain, Menu, Tray } = require('electron');
const path = require('node:path');
const fs = require('node:fs/promises');
const fsSync = require('node:fs');
const { ProcessRunner } = require('./process-runner');

const isUnpacked = process.resourcesPath.includes(`${path.sep}dist${path.sep}win-unpacked${path.sep}resources`);
const root = app.isPackaged ? (process.env.PORTABLE_EXECUTABLE_DIR || (isUnpacked ? path.resolve(process.resourcesPath, '..', '..', '..', 'data') : path.dirname(process.execPath))) : path.resolve(__dirname, '..', '..');
if (isUnpacked) {
  const legacyData = path.resolve(process.resourcesPath, '..', 'data');
  for (const name of ['control.json', 'account.json', 'scan-status.json']) {
    const source = path.join(legacyData, name);
    const destination = path.join(root, 'data', name);
    if (fsSync.existsSync(source) && !fsSync.existsSync(destination)) {
      fsSync.mkdirSync(path.dirname(destination), { recursive: true });
      fsSync.copyFileSync(source, destination);
    }
  }
}
const smokeTest = process.argv.includes('--smoke-test');
app.setPath('userData', path.join(root, 'data', smokeTest ? 'electron-smoke' : 'electron'));
const runner = new ProcessRunner(root, undefined, { managePath: app.isPackaged ? path.join(process.resourcesPath, 'manage.exe') : null });
let window;
let tray;

function showWindow() {
  if (!window) createWindow();
  window.show();
  window.focus();
}

if (!smokeTest && !app.requestSingleInstanceLock()) process.exit(0);
app.on('second-instance', () => {
  if (window) {
    if (window.isMinimized()) window.restore();
    window.focus();
  }
});

function sendLog(message) {
  if (window && !window.isDestroyed()) window.webContents.send('log', message);
}

function createWindow() {
  window = new BrowserWindow({
    width: 1080,
    height: 800,
    minWidth: 900,
    minHeight: 760,
    backgroundColor: '#f4f4f2',
    title: '火花',
    icon: path.join(__dirname, '..', 'assets', 'icon.ico'),
    autoHideMenuBar: true,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
    },
  });
  window.loadFile(path.join(__dirname, 'renderer', 'index.html'));
  window.on('close', (event) => {
    if (!smokeTest) {
      event.preventDefault();
      window.hide();
    }
  });
  window.on('minimize', (event) => {
    event.preventDefault();
    window.hide();
  });
  window.on('closed', () => { window = null; });
}

function createTray() {
  tray = new Tray(path.join(__dirname, '..', 'assets', 'icon.ico'));
  tray.setToolTip('火花');
  tray.on('click', showWindow);
  tray.setContextMenu(Menu.buildFromTemplate([
    { label: '打开火花', click: showWindow },
    { type: 'separator' },
    { label: '退出', click: () => app.quit() },
  ]));
}

app.on('will-quit', () => {
  if (tray) tray.destroy();
});

ipcMain.handle('status', async () => {
  const result = await runner.run('status');
  const config = JSON.parse((await runner.run('config')).output);
  const accountStatus = JSON.parse((await runner.run('accountStatus')).output);
  return {
    raw: result.output,
    loggedIn: ['webbridge', 'default'].includes(config.browser_mode) || result.output.includes('独立登录状态: 已保存'),
    enabled: result.output.includes('自动发送: 已启用'),
    watching: runner.watching,
    config,
    account: accountStatus.account,
    scan: accountStatus.scan,
  };
});
ipcMain.handle('save-config', (_event, settings) => runner.saveConfig(settings));
ipcMain.handle('login', () => runner.run('login'));
ipcMain.handle('dry-run', () => runner.run('dryRun'));
ipcMain.handle('watch', async (_event, confirmation) => {
  if (confirmation !== true) throw new Error('需要确认后才能开启');
  const status = await runner.run('status');
  const config = JSON.parse((await runner.run('config')).output);
  if (!['webbridge', 'default'].includes(config.browser_mode) && !status.output.includes('独立登录状态: 已保存')) throw new Error('请先登录抖音');
  runner.startWatch(sendLog, () => sendLog('常驻监视已停止'));
  return { watching: true };
});
ipcMain.handle('pause', () => runner.stopWatch());
ipcMain.handle('logs', async () => {
  try {
    const content = await fs.readFile(path.join(root, 'logs', 'run.log'), 'utf8');
    return content.split(/\r?\n/).slice(-80).join('\n');
  } catch (error) {
    if (error.code === 'ENOENT') return '还没有运行日志。';
    throw error;
  }
});

app.whenReady().then(() => {
  createWindow();
  if (!smokeTest) createTray();
  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on('before-quit', (event) => {
  if (!runner.watching) return;
  event.preventDefault();
  runner.stopWatch().finally(() => app.exit(0));
});

if (process.argv.includes('--smoke-test')) {
  app.whenReady().then(async () => {
    window.setSize(400, 520);
    await new Promise((resolve) => setTimeout(resolve, 1200));
    const result = await window.webContents.executeJavaScript(`({
      title: document.title,
      heading: document.querySelector('h1')?.textContent,
      dryRun: document.querySelector('#scan')?.textContent,
      scanDisabled: document.querySelector('#scan')?.disabled,
      loginRequired: document.querySelector('#login-status')?.textContent.includes('需要登录'),
      clientHeight: document.documentElement.clientHeight,
      scrollHeight: document.documentElement.scrollHeight,
      node: typeof require,
      api: typeof window.spark?.status
    })`);
    console.log(JSON.stringify(result));
    const interaction = await window.webContents.executeJavaScript(`(async () => {
      for (let i = 0; i < 300 && !settingsLoaded; i++) await new Promise(resolve => setTimeout(resolve, 100));
      loggedIn = true;
      updateControls();
      const enabledAfterLogin = !document.querySelector('#scan').disabled;
      const webbridgeMode = currentConfig.browser_mode === 'webbridge';
      if (!webbridgeMode) document.querySelector('#scan').click();
      for (let i = 0; i < 300 && busy; i++) await new Promise(resolve => setTimeout(resolve, 100));
      const scanFeedback = webbridgeMode ? 'WebBridge 由独立真实页面测试覆盖' : document.querySelector('#toast').textContent;
      document.querySelector('#settings-form').requestSubmit();
      for (let i = 0; i < 300 && busy; i++) await new Promise(resolve => setTimeout(resolve, 100));
      document.querySelector('input[name="message-type"][value="sticker"]').click();
      document.querySelector('#sticker-current').click();
      const stickerCount = document.querySelectorAll('#sticker-options button').length;
      document.querySelector('#sticker-options button[data-name="续火花"]').click();
      await new Promise(resolve => setTimeout(resolve, 300));
      const selectedSticker = document.querySelector('#sticker-current-name').textContent;
      const stickerImageLoaded = document.querySelector('#sticker-current-image').naturalWidth > 0;
      document.querySelector('[data-view="logs"]').click();
      await new Promise(resolve => setTimeout(resolve, 150));
      const logsVisible = !document.querySelector('#logs-view').hidden && document.querySelector('#page-title').textContent === '运行记录';
      document.querySelector('[data-view="overview"]').click();
      await new Promise(resolve => setTimeout(resolve, 150));
      return {
        enabledAfterLogin,
        feedback: document.querySelector('#toast').textContent,
        scanFeedback,
        settingsSaved: document.querySelector('#settings-status').textContent,
        scheduleTime: document.querySelector('#schedule-time').textContent,
        logsVisible,
        stickerCount,
        selectedSticker,
        stickerImageLoaded,
      };
    })()`);
    console.log(JSON.stringify(interaction));
    await fs.mkdir(path.join(root, 'artifacts'), { recursive: true });
    await window.webContents.capturePage().then((image) => fs.writeFile(path.join(root, 'artifacts', 'desktop-smoke.png'), image.toPNG()));
    const failed = result.scrollHeight > result.clientHeight || result.node !== 'undefined' || result.api !== 'function' || (result.loginRequired && !result.scanDisabled) || !interaction.enabledAfterLogin || !(interaction.scanFeedback.includes('尚未完成独立浏览器登录') || interaction.scanFeedback.includes('WebBridge')) || !interaction.feedback.includes('发送设置已保存') || interaction.settingsSaved !== '已保存' || !interaction.logsVisible || interaction.stickerCount !== 12 || interaction.selectedSticker !== '续火花' || !interaction.stickerImageLoaded;
    await fs.writeFile(path.join(root, 'artifacts', 'smoke-result.json'), JSON.stringify({ result, interaction, failed }));
    app.exit(failed ? 1 : 0);
  });
}
