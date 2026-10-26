# 火花管家

这是专门的 Electron 桌面小应用，不是 Agent 平台。Electron 提供简洁界面，Python `manage.py` 是唯一自动化执行器，不接入 Claude、Codex、CCSwitch 或云端 Agent。

## 约束

- 所有依赖、日志和缓存只能留在项目目录。不得读取或输出 `data/storage-state.json`、Cookie、日常浏览器资料或 CCSwitch 配置。优先使用 Kimi WebBridge 操作当前浏览器，通过固定 `spark-keeper` 会话和本机 HTTP 接口调用；不要切换会话或关闭用户标签页。默认 Chrome 备用模式不得复制配置，被占用时停止，不强关浏览器。
- 按 `data/control.json` 的时间扫描所有灰色火花，各发一次配置的文字或原生表情；已点亮跳过；状态不明不发。
- 未获用户当次明确确认，不得真实发送或启用自动发送。Dry Run 不得调用发送路径。
- Electron 使用安全 preload IPC，渲染层不能传任意命令。新增操作必须加入固定参数白名单并补测试。
- 修改 Python 后运行 `.venv/Scripts/python.exe -m pytest -q`；修改 Electron 后在 `desktop/` 运行 `npm test` 和 `npm run smoke`。
- 不绕过验证码、安全验证或平台风控。

## 入口

- 图形应用：双击根目录 `火花管家.vbs`，不得使用会弹出控制台的启动器。
- 状态：`python manage.py status`
- 登录：`python manage.py login`
- 不发送测试：`python manage.py dry-run`
- 真实单轮：`python manage.py run --confirm-send`
- 常驻模式：`python manage.py watch --confirm-send`
- 暂停：`python manage.py pause`
- Windows 定时：`python manage.py resume`
- 停用并删除定时任务：`python manage.py uninstall`

Electron 源码在 `desktop/`，界面只保留登录、扫描、23 点自动开关和简短日志，不增加 Agent 会话或设置中心。
