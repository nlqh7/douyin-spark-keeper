from __future__ import annotations

import argparse
from datetime import datetime, timedelta
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import venv
from zoneinfo import ZoneInfo

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
    sys.stderr.reconfigure(encoding="utf-8", errors="backslashreplace")

from app.control import normalize_control


FROZEN = bool(getattr(sys, "frozen", False))
ROOT = Path(os.environ.get("SPARK_ROOT", Path(__file__).resolve().parent))
VENV = ROOT / ".venv"
VENV_PYTHON = Path(sys.executable) if FROZEN else VENV / "Scripts" / "python.exe"
DATA_DIR = ROOT / "data"
CONTROL_PATH = DATA_DIR / "control.json"
TASK_NAME = "DouyinSpark23"
NO_WINDOW = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
os.environ["PLAYWRIGHT_BROWSERS_PATH"] = str(ROOT / "browser")
os.environ["PIP_CACHE_DIR"] = str(ROOT / ".pip-cache")


def project_env() -> dict[str, str]:
    env = os.environ.copy()
    env["PLAYWRIGHT_BROWSERS_PATH"] = str(ROOT / "browser")
    env["PIP_CACHE_DIR"] = str(ROOT / ".pip-cache")
    env["PYTHONIOENCODING"] = "utf-8"
    return env


def load_control() -> dict:
    try:
        value = json.loads(CONTROL_PATH.read_text(encoding="utf-8"))
    except FileNotFoundError:
        value = {}
    return normalize_control(value)


def save_control(control: dict) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    temporary = CONTROL_PATH.with_suffix(".tmp")
    temporary.write_text(json.dumps(control, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(CONTROL_PATH)


def in_project_venv() -> bool:
    try:
        return Path(sys.executable).resolve() == VENV_PYTHON.resolve()
    except OSError:
        return False


def reexec_in_venv(arguments: list[str]) -> int:
    if in_project_venv():
        return -1
    if not VENV_PYTHON.is_file():
        print("尚未安装运行环境，请先执行: python manage.py setup")
        return 2
    return subprocess.run([str(VENV_PYTHON), str(ROOT / "manage.py"), *arguments], cwd=ROOT, env=project_env()).returncode


def setup() -> int:
    if not VENV_PYTHON.is_file():
        print("创建项目内 Python 虚拟环境……")
        venv.EnvBuilder(with_pip=True).create(VENV)
    env = project_env()
    print("安装项目内依赖……")
    subprocess.run(
        [str(VENV_PYTHON), "-m", "pip", "install", "-r", str(ROOT / "requirements.txt")],
        cwd=ROOT,
        env=env,
        check=True,
    )
    from app.local_browser import find_system_browser

    if find_system_browser():
        print("使用已安装的 Chrome/Edge；登录状态仍独立保存在项目 data 目录。")
    else:
        print("未检测到 Chrome/Edge，安装项目内 Chromium……")
        subprocess.run(
            [str(VENV_PYTHON), "-m", "playwright", "install", "chromium"],
            cwd=ROOT,
            env=env,
            check=True,
        )
    if not CONTROL_PATH.exists():
        save_control({"enabled": False, "headless": False})
    print("安装完成。所有运行文件均位于:", ROOT)
    print("下一步: python manage.py login")
    return 0


def login() -> int:
    from app.login_local import login as login_browser

    import asyncio

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if load_control()["browser_mode"] == "webbridge":
        from app.webbridge import ensure_chat
        ensure_chat()
        print("已在当前 Chrome 打开抖音私信。")
        return 0
    asyncio.run(login_browser(DATA_DIR / "storage-state.json", load_control()["browser_mode"]))
    return 0


def status() -> int:
    control = load_control()
    print("项目目录:", ROOT)
    print("运行环境:", "已安装" if VENV_PYTHON.is_file() else "未安装")
    print("独立登录状态:", "已保存" if (DATA_DIR / "storage-state.json").is_file() else "未登录")
    print("自动发送:", "已启用" if control.get("enabled") else "未启用")
    kind = "原生表情" if control["message_type"] == "sticker" else "文本"
    print(f"发送规则: 每天 {control['time']}，所有灰色火花各发送一次{kind}“{control['content']}”")
    result = subprocess.run(
        ["schtasks", "/Query", "/TN", TASK_NAME, "/FO", "LIST"],
        capture_output=True,
        text=True,
        errors="replace",
        creationflags=NO_WINDOW,
    )
    if result.returncode:
        print("Windows 定时任务: 未创建")
    else:
        print("Windows 定时任务:")
        for line in result.stdout.splitlines():
            if any(key in line for key in ("TaskName", "Next Run Time", "Status", "任务名", "下次运行时间", "状态")):
                print(" ", line.strip())
    return 0


def show_config() -> int:
    print(json.dumps(load_control(), ensure_ascii=False))
    return 0


def account_status() -> int:
    from app.account import account_status as read_account_status

    print(json.dumps(read_account_status(), ensure_ascii=False))
    return 0


def configure(args: argparse.Namespace) -> int:
    control = load_control()
    control.update({"time": args.time, "message_type": args.message_type, "content": args.content, "browser_mode": args.browser_mode})
    save_control(normalize_control(control))
    print("设置已保存。")
    return 0


def pause() -> int:
    control = load_control()
    control["enabled"] = False
    save_control(control)
    result = subprocess.run(["schtasks", "/Change", "/TN", TASK_NAME, "/DISABLE"], capture_output=True, text=True, errors="replace", creationflags=NO_WINDOW)
    if result.returncode:
        print("自动发送已关闭；定时任务当前未创建或已删除。")
    else:
        print("自动发送已暂停，定时任务已禁用。")
    return 0


def resume() -> int:
    if not VENV_PYTHON.is_file() or not (DATA_DIR / "storage-state.json").is_file():
        print("启用前必须完成 setup 和 login。")
        return 2
    control = load_control()
    command = f'"{VENV_PYTHON}" "{ROOT / "manage.py"}" run --scheduled'
    result = subprocess.run(
        ["schtasks", "/Create", "/TN", TASK_NAME, "/SC", "DAILY", "/ST", control["time"], "/TR", command, "/F"],
        capture_output=True,
        text=True,
        errors="replace",
        creationflags=NO_WINDOW,
    )
    if result.returncode:
        print(result.stderr or result.stdout)
        return result.returncode
    subprocess.run(["schtasks", "/Change", "/TN", TASK_NAME, "/ENABLE"], check=True, capture_output=True, creationflags=NO_WINDOW)
    control = load_control()
    control["enabled"] = True
    save_control(control)
    print("已启用唯一任务 DouyinSpark23：每天 23:00 检查所有灰色火花。")
    return 0


def uninstall() -> int:
    control = load_control()
    control["enabled"] = False
    save_control(control)
    result = subprocess.run(["schtasks", "/Delete", "/TN", TASK_NAME, "/F"], capture_output=True, text=True, errors="replace", creationflags=NO_WINDOW)
    if result.returncode:
        print("定时任务不存在或已删除。")
    else:
        print("已删除定时任务 DouyinSpark23。")
    print("自动化已停用。剩余内容全部位于:", ROOT)
    print("确认不再需要登录状态和日志后，删除该整个目录即完成清理。")
    return 0


def execute(dry_run: bool, scheduled: bool) -> int:
    from app.guarded import execute as execute_guarded

    try:
        return execute_guarded(dry_run=dry_run, scheduled=scheduled)
    except Exception as exc:
        print("错误:", exc)
        return 2


def next_send_time(now: datetime, time_value: str = "23:00") -> datetime:
    hour, minute = (int(part) for part in time_value.split(":"))
    candidate = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    return candidate if now < candidate else candidate + timedelta(days=1)


def watch() -> int:
    control = load_control()
    control["enabled"] = True
    control["mode"] = "watch"
    save_control(control)
    print("常驻监视已启动；保持本窗口开着，按 Ctrl+C 可停止。")
    print(f"规则：每天 {control['time']}，所有灰色火花各发送一次“{control['content']}”。")
    try:
        while True:
            if not load_control().get("enabled"):
                print("自动发送已被暂停，监视退出。")
                return 0
            now = datetime.now(ZoneInfo("Asia/Shanghai"))
            target = next_send_time(now, load_control()["time"])
            print("下次检查时间:", target.strftime("%Y-%m-%d %H:%M:%S %Z"))
            while True:
                remaining = (target - datetime.now(ZoneInfo("Asia/Shanghai"))).total_seconds()
                if remaining <= 0:
                    break
                time.sleep(min(remaining, 30))
                if not load_control().get("enabled"):
                    print("自动发送已被暂停，监视退出。")
                    return 0
            if datetime.now(ZoneInfo("Asia/Shanghai")) > target + timedelta(minutes=10):
                print("本次 23 点任务因电脑睡眠等原因错过，已跳过，不补发。")
            else:
                execute(dry_run=False, scheduled=False)
    except KeyboardInterrupt:
        control = load_control()
        control["enabled"] = False
        control["mode"] = None
        save_control(control)
        print("\n常驻监视已停止，自动发送已关闭。")
        return 0


def console() -> int:
    actions = {
        "1": lambda: status(),
        "2": lambda: login(),
        "3": lambda: execute(dry_run=True, scheduled=False),
        "5": lambda: pause(),
    }
    while True:
        print("\n=== 抖音续火花控制终端 ===")
        print("1. 查看状态    2. 扫码登录    3. Dry Run（不发送）")
        print("4. 开始常驻监视（真实发送）    5. 暂停自动发送    6. 退出")
        try:
            choice = input("请选择 [1-6]: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return 0
        if choice == "6":
            return 0
        if choice == "4":
            confirmation = input("启动后每天 23:00 会真实发送，输入 YES 确认: ").strip()
            if confirmation == "YES":
                return watch()
            print("未确认，未启动监视。")
            continue
        action = actions.get(choice)
        if action is None:
            print("无效选择。")
            continue
        action()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="受控的抖音灰色火花续火工具")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("setup", help="安装到当前目录，不修改系统 Python")
    subparsers.add_parser("login", help="打开独立浏览器，扫码并保存登录状态")
    subparsers.add_parser("console", help="打开交互式控制终端")
    subparsers.add_parser("status", help="查看安装、登录和定时任务状态")
    subparsers.add_parser("config", help="输出当前本地设置")
    subparsers.add_parser("account-status", help="输出当前账号和待续火花状态")
    configure_parser = subparsers.add_parser("configure", help="保存时间、文字或原生表情设置")
    configure_parser.add_argument("--time", required=True)
    configure_parser.add_argument("--message-type", choices=("text", "sticker"), required=True)
    configure_parser.add_argument("--content", required=True)
    configure_parser.add_argument("--browser-mode", choices=("webbridge", "isolated", "default"), required=True)
    subparsers.add_parser("dry-run", help="只扫描并核对灰色火花，不发送")
    run_parser = subparsers.add_parser("run", help="执行真实发送")
    run_parser.add_argument("--confirm-send", action="store_true", help="明确允许本次真实发送")
    run_parser.add_argument("--scheduled", action="store_true", help=argparse.SUPPRESS)
    watch_parser = subparsers.add_parser("watch", help="保持终端开着，每天 23:00 执行")
    watch_parser.add_argument("--confirm-send", action="store_true", help="明确允许常驻真实发送")
    subparsers.add_parser("pause", help="关闭自动发送并禁用定时任务")
    subparsers.add_parser("resume", help="创建并启用每天 23:00 的唯一任务")
    subparsers.add_parser("uninstall", help="停用自动化并删除定时任务")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.command == "setup":
        return setup()
    if args.command == "status":
        return status()
    if args.command == "config":
        return show_config()
    if args.command == "account-status":
        return account_status()
    if args.command == "configure":
        return configure(args)
    if args.command == "pause":
        return pause()
    if args.command == "resume":
        return resume()
    if args.command == "uninstall":
        return uninstall()
    delegated = reexec_in_venv(sys.argv[1:])
    if delegated >= 0:
        return delegated
    if args.command == "login":
        return login()
    if args.command == "console":
        return console()
    if args.command == "dry-run":
        return execute(dry_run=True, scheduled=False)
    if args.command == "watch":
        if not args.confirm_send:
            print("常驻真实发送需要明确添加 --confirm-send；也可以直接运行 console。")
            return 2
        return watch()
    if args.command == "run":
        if not args.scheduled and not args.confirm_send:
            print("真实发送需要明确添加 --confirm-send；日常检查请使用 dry-run。")
            return 2
        return execute(dry_run=False, scheduled=args.scheduled)
    return 2


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print("程序执行失败:", exc)
        raise SystemExit(2)
