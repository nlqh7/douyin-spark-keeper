const { spawn } = require('node:child_process');
const path = require('node:path');

const COMMANDS = Object.freeze({
  status: ['status'],
  config: ['config'],
  accountStatus: ['account-status'],
  login: ['login'],
  dryRun: ['dry-run'],
  pause: ['pause'],
  watch: ['watch', '--confirm-send'],
});

function commandArguments(name, confirmed = false) {
  if (!Object.hasOwn(COMMANDS, name)) throw new Error('不支持的操作');
  if (name === 'watch' && confirmed !== true) throw new Error('自动续火需要明确确认');
  return [...COMMANDS[name]];
}

function configArguments(settings) {
  const time = typeof settings?.time === 'string' ? settings.time : '';
  const match = /^(?:[01]\d|2[0-3]):[0-5]\d$/.test(time);
  if (!match) throw new Error('请输入有效时间');
  const messageType = settings.messageType;
  const content = typeof settings.content === 'string' ? settings.content.trim() : '';
  if (!['text', 'sticker'].includes(messageType)) throw new Error('消息类型无效');
  if (!content || content.length > 20 || /[\r\n]/.test(content)) throw new Error('发送内容需为 1-20 个字符的单行文本');
  if (messageType === 'sticker' && !['续火花', '晚上好', '比心', '早上好', '早点睡', '在干嘛', '开心', '嗨', '爱心', '绝了', '笑死', '已阅'].includes(content)) throw new Error('不支持这个原生表情');
  const browserMode = settings.browserMode || 'isolated';
  if (!['webbridge', 'isolated', 'default'].includes(browserMode)) throw new Error('浏览器模式无效');
  return ['configure', '--time', time, '--message-type', messageType, '--content', content, '--browser-mode', browserMode];
}

class ProcessRunner {
  constructor(root, spawnImpl = spawn, options = {}) {
    this.root = root;
    this.spawnImpl = spawnImpl;
    this.python = options.managePath || path.join(root, '.venv', 'Scripts', 'python.exe');
    this.manage = options.managePath ? null : path.join(root, 'manage.py');
    this.watchChild = null;
  }

  run(name, customArgs = null) {
    const args = customArgs || commandArguments(name);
    return new Promise((resolve, reject) => {
      const child = this.spawnImpl(this.python, [...(this.manage ? [this.manage] : []), ...args], {
        cwd: this.root,
        windowsHide: true,
        creationflags: 0x08000000,
        env: { ...process.env, PYTHONIOENCODING: 'utf-8', SPARK_ROOT: this.root },
      });
      let stdout = '';
      let stderr = '';
      child.stdout.on('data', (chunk) => { stdout += chunk.toString(); });
      child.stderr.on('data', (chunk) => { stderr += chunk.toString(); });
      child.on('error', reject);
      child.on('close', (code) => {
        if (code === 0) resolve({ output: stdout.trim() });
        else reject(new Error((stderr || stdout || `操作失败（${code}）`).trim()));
      });
    });
  }

  saveConfig(settings) {
    return this.run(null, configArguments(settings));
  }

  startWatch(onOutput, onExit) {
    if (this.watchChild) return;
    const args = commandArguments('watch', true);
    const child = this.spawnImpl(this.python, [...(this.manage ? [this.manage] : []), ...args], {
      cwd: this.root,
      windowsHide: true,
      creationflags: 0x08000000,
      env: { ...process.env, PYTHONIOENCODING: 'utf-8', SPARK_ROOT: this.root },
    });
    this.watchChild = child;
    child.stdout.on('data', (chunk) => onOutput(chunk.toString()));
    child.stderr.on('data', (chunk) => onOutput(chunk.toString()));
    child.on('error', (error) => {
      this.watchChild = null;
      onOutput(error.message);
    });
    child.on('close', () => {
      this.watchChild = null;
      onExit();
    });
  }

  async stopWatch() {
    const child = this.watchChild;
    this.watchChild = null;
    if (child && child.exitCode === null) child.kill();
    await this.run('pause');
  }

  get watching() {
    return this.watchChild !== null;
  }
}

module.exports = { COMMANDS, ProcessRunner, commandArguments, configArguments };
