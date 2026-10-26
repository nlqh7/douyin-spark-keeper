# 火花

一个专门给抖音续火花的 Windows 桌面小工具。每天定时检查私信列表，给所有灰色火花各发一次设置的文字或抖音原生表情。

界面使用 Electron，浏览器操作通过 Kimi WebBridge 在你当前登录的 Chrome 中完成，不导出 Cookie，也不需要重新登录或开启 Chrome 调试端口。

## 下载即用

1. 从 Releases 下载 `SparkKeeper-x.x.x-win-x64.exe`。
2. 在 Chrome 中安装并启用 [Kimi WebBridge](https://www.kimi.com/zh-cn/features/webbridge)，确认本机桥接服务已开启。
3. 双击 EXE。无需安装 Python、Node.js 或额外浏览器。
4. 在“浏览器连接”中选择 **Kimi WebBridge**，先点“扫描火花”。扫描只会打开并核对会话，不发送消息。
5. 确认结果后设置时间、文字或原生表情，再开启“自动续火”。

首次打开 WebBridge 创建的“火花管家”标签组后请保留。它会在当前 Chrome 中运行，不会读取你的日常浏览器配置文件。

## 功能

- 扫描全部灰色火花，已点亮的跳过。
- 自定义每天执行时间。
- 自定义单行文字，或选择“晚上好”“比心”原生表情。
- Dry Run 不发送；每天每个对象最多处理一次；结果不确定不重发。
- 所有依赖已打入单个便携 EXE，无控制台窗口、无安装器、无开机启动。

## 使用和卸载

- 保持应用、电脑和 Chrome 运行。电脑睡眠会导致任务错过，错过后不补发。
- 配置和日志保存在 EXE 同目录的 `data/`、`logs/`。
- 删除 EXE 及这两个目录即可卸载；不会删除你的 Chrome 或 WebBridge。

## 本地开发

```powershell
python -m venv .venv
.venv\Scripts\pip install -r requirements-dev.txt
.venv\Scripts\python manage.py setup
cd desktop
npm install
npm test
npm start
```

完整测试：

```powershell
.venv\Scripts\python -m pytest -q
cd desktop
npm test
npm run smoke
```

## 构建便携版

```powershell
.venv\Scripts\pip install pyinstaller pillow
.venv\Scripts\python scripts/build_assets.py
.venv\Scripts\python -m PyInstaller --noconfirm --onefile --noconsole --name manage --collect-all playwright --collect-all tzdata --distpath build --workpath build/work --specpath build/spec manage.py
cd desktop
npm run dist
```

## 风险说明

网页自动化可能因抖音页面变化、登录失效或平台风控而停止。请仅用于本人账号和正常社交互动，不保证单方面发送一定能完成双方互动规则。遇到验证码或安全验证时应人工处理，本项目不尝试绕过。

## 来源与许可

基于 [unmev/douyin-auto-fire](https://github.com/unmev/douyin-auto-fire) 的浏览器自动化和发送确认逻辑，加入 Electron 界面、Kimi WebBridge 后端、受控配置和便携打包。保留原项目的 PolyForm Noncommercial 许可，仅限非商业用途，详见 `LICENSE`。
