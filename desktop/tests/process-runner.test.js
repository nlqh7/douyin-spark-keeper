const test = require('node:test');
const assert = require('node:assert/strict');
const path = require('node:path');
const { EventEmitter } = require('node:events');
const { commandArguments, configArguments, ProcessRunner } = require('../src/process-runner');

function fakeChild() {
  const child = new EventEmitter();
  child.stdout = new EventEmitter();
  child.stderr = new EventEmitter();
  child.exitCode = null;
  child.kill = () => { child.exitCode = 0; };
  return child;
}

test('only fixed management commands are available', () => {
  assert.deepEqual(commandArguments('dryRun'), ['dry-run']);
  assert.deepEqual(commandArguments('status'), ['status']);
  assert.throws(() => commandArguments('shell'), /不支持/);
});

test('watch cannot be started without explicit confirmation', () => {
  assert.deepEqual(commandArguments('watch', true), ['watch', '--confirm-send']);
  assert.throws(() => commandArguments('watch'), /明确确认/);
  assert.throws(() => commandArguments('watch', 'yes'), /明确确认/);
});

test('python is spawned directly with fixed arguments and project cwd', async () => {
  const child = fakeChild();
  let invocation;
  const runner = new ProcessRunner('D:\\spark', (...args) => {
    invocation = args;
    queueMicrotask(() => child.emit('close', 0));
    return child;
  });

  await runner.run('dryRun');

  assert.equal(invocation[0], path.join('D:\\spark', '.venv', 'Scripts', 'python.exe'));
  assert.deepEqual(invocation[1], [path.join('D:\\spark', 'manage.py'), 'dry-run']);
  assert.equal(invocation[2].cwd, 'D:\\spark');
  assert.equal(invocation[2].shell, undefined);
});

test('watch is a singleton and stop always revokes automation permission', async () => {
  const child = fakeChild();
  const calls = [];
  const runner = new ProcessRunner('D:\\spark', (executable, args) => {
    calls.push(args.at(-1));
    if (args.at(-1) === 'pause') queueMicrotask(() => child.emit('close', 0));
    return child;
  });

  runner.startWatch(() => {}, () => {});
  runner.startWatch(() => {}, () => {});
  assert.equal(calls.filter((arg) => arg === '--confirm-send').length, 1);
  assert.equal(runner.watching, true);
  await runner.stopWatch();
  assert.equal(runner.watching, false);
  assert.equal(calls.at(-1), 'pause');
});

test('custom schedule and message are passed as separate safe arguments', () => {
  assert.deepEqual(configArguments({ time: '22:45', messageType: 'text', content: '🔥' }), [
    'configure', '--time', '22:45', '--message-type', 'text', '--content', '🔥', '--browser-mode', 'isolated',
  ]);
  assert.deepEqual(configArguments({ time: '23:00', messageType: 'sticker', content: '比心', browserMode: 'default' }), [
    'configure', '--time', '23:00', '--message-type', 'sticker', '--content', '比心', '--browser-mode', 'default',
  ]);
});

test('invalid schedule and unsafe content are rejected before spawning', () => {
  assert.throws(() => configArguments({ time: '25:00', messageType: 'text', content: '火' }), /有效时间/);
  assert.throws(() => configArguments({ time: '23:00', messageType: 'text', content: '火\nrm' }), /单行/);
  assert.throws(() => configArguments({ time: '23:00', messageType: 'sticker', content: '任意图' }), /不支持/);
});
