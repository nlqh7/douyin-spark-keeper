from __future__ import annotations

import json
import logging
import os
from datetime import datetime
from pathlib import Path
import time
from types import SimpleNamespace

from app.browser import AuthenticationError, RiskControlError, open_douyin, open_private_messages, verify_login
from app.control import message_for_control, normalize_control
from app.douyin import DouyinChat
from app.history import History, run_lock
from app.local_browser import find_system_browser
from app.main import _configure_logging
from app.models import Message, Settings
from app.privacy import build_target_aliases, target_alias
from app.profile_browser import open_default_chrome
from app.sender import send_message
from app.streaks import discover_streak_friends


ROOT = Path(os.environ.get("SPARK_ROOT", Path(__file__).resolve().parents[1]))
DATA_DIR = ROOT / "data"
CONTROL_PATH = DATA_DIR / "control.json"
LOG_DIR = ROOT / "logs"
TASK_ID = "guarded-gray-streak"


def load_control() -> dict:
    try:
        value = json.loads(CONTROL_PATH.read_text(encoding="utf-8"))
    except FileNotFoundError:
        value = {}
    return normalize_control(value)


def settings_for_run() -> Settings:
    control = load_control()
    state = DATA_DIR / "storage-state.json"
    if control["browser_mode"] == "isolated" and not state.is_file():
        raise ValueError("尚未完成独立浏览器登录，请先运行 login")
    return Settings(
        task_config_path=DATA_DIR / "unused.json",
        storage_state=str(state) if state.is_file() else None,
        cookie=None,
        headless=bool(control.get("headless", False)),
        browser_path=find_system_browser(),
        artifacts_dir=LOG_DIR,
        trace=False,
    )


async def run_guarded(*, dry_run: bool, scheduled: bool = False) -> int:
    control = load_control()
    if scheduled and not control.get("enabled"):
        raise ValueError("自动任务尚未启用")
    if control["browser_mode"] == "webbridge":
        from app.webbridge_runner import run_webbridge
        return run_webbridge(control, LOG_DIR, dry_run=dry_run)
    message, stickers = message_for_control(control)
    settings = settings_for_run()
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    _configure_logging(LOG_DIR, reset=True)
    logger = logging.getLogger("douyin_sender")
    history = History(LOG_DIR / "history.json")
    run_date = history.run_date("Asia/Shanghai")
    results: list[dict] = []
    browser_session = open_default_chrome(headless=settings.headless) if control["browser_mode"] == "default" else open_douyin(settings)

    async with browser_session as session:
        page = session.page
        try:
            await open_private_messages(page)
            friends = await discover_streak_friends(page, needs_renewal_only=True)
            aliases = build_target_aliases(tuple(SimpleNamespace(name=name) for name in friends))
            _configure_logging(LOG_DIR, aliases)
            logger.info("识别到 %d 个灰色火花对象", len(friends))
            chat = DouyinChat(page, timeout_ms=15_000)

            for index, name in enumerate(friends):
                alias = target_alias(index)
                key = history.key(TASK_ID, run_date, name, "text-fire")
                try:
                    if history.contains(key):
                        logger.info("当天已处理或结果不确定，跳过: %s", alias)
                        results.append({"target": alias, "status": "skipped"})
                        continue
                    await chat.open_target(name, retries=0)
                    if dry_run:
                        results.append({"target": alias, "status": "dry-run"})
                        continue

                    history.reserve(key)
                    await verify_login(page, timeout_ms=3_000)
                    await send_message(page, chat, message, stickers)
                    history.mark_success(key)
                    results.append({"target": alias, "status": "sent"})
                    logger.info("已发送并确认: %s", alias)
                except (AuthenticationError, RiskControlError):
                    raise
                except Exception as exc:
                    logger.exception("对象处理失败: %s", alias)
                    results.append({"target": alias, "status": "failed", "error": str(exc)})
        except Exception as exc:
            logger.exception("续火花任务停止")
            results.append({"target": "run", "status": "failed", "error": str(exc)})
            _write_results(results, dry_run)
            await _save_failure_screenshot(page)
            raise

    _write_results(results, dry_run)
    return 1 if any(item["status"] == "failed" for item in results) else 0


def _write_results(results: list[dict], dry_run: bool) -> None:
    payload = {
        "finished_at": datetime.now().astimezone().isoformat(),
        "dry_run": dry_run,
        "message": load_control()["content"],
        "results": results,
    }
    temporary = LOG_DIR / "result.json.tmp"
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(LOG_DIR / "result.json")


async def _save_failure_screenshot(page) -> None:
    directory = LOG_DIR / "screenshots"
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{datetime.now():%Y%m%d-%H%M%S}-failure.png"
    try:
        await page.screenshot(path=path, full_page=True)
    except Exception:
        logging.getLogger("douyin_sender").exception("失败截图保存失败")


def cleanup_artifacts(now: float | None = None) -> None:
    now = time.time() if now is None else now
    cutoff = now - 14 * 24 * 60 * 60
    screenshot_dir = LOG_DIR / "screenshots"
    if screenshot_dir.is_dir():
        for path in screenshot_dir.glob("*.png"):
            if path.is_file() and path.stat().st_mtime < cutoff:
                path.unlink()
    run_log = LOG_DIR / "run.log"
    if run_log.is_file() and run_log.stat().st_size > 5 * 1024 * 1024:
        run_log.replace(LOG_DIR / "run.log.1")


def execute(*, dry_run: bool, scheduled: bool = False) -> int:
    import asyncio

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    cleanup_artifacts()
    with run_lock(LOG_DIR / "run.lock"):
        return asyncio.run(run_guarded(dry_run=dry_run, scheduled=scheduled))
