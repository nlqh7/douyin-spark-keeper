from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path

from app.control import message_for_control
from app.history import History
from app.main import _configure_logging
from app.privacy import target_alias
from app.webbridge import deactivate_page, discover_gray_streaks, ensure_chat, open_target, send_sticker, send_text


TASK_ID = "guarded-gray-streak"


def _run_webbridge(control: dict, log_dir: Path, *, dry_run: bool) -> int:
    log_dir.mkdir(parents=True, exist_ok=True)
    _configure_logging(log_dir, reset=True)
    logger = logging.getLogger("douyin_sender")
    history = History(log_dir / "history.json")
    run_date = history.run_date("Asia/Shanghai")
    message, _ = message_for_control(control)
    results = []

    ensure_chat()
    friends = discover_gray_streaks()
    scan_status_path = log_dir.parent / "data" / "scan-status.json"
    scan_status_path.parent.mkdir(parents=True, exist_ok=True)
    scan_status_path.write_text(json.dumps({"count": len(friends), "targets": friends}, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info("WebBridge 识别到 %d 个灰色火花对象", len(friends))
    for index, name in enumerate(friends):
        alias = target_alias(index)
        key = history.key(TASK_ID, run_date, name, "daily-renewal")
        try:
            if history.contains(key):
                results.append({"target": alias, "status": "skipped"})
                continue
            open_target(name)
            if dry_run:
                results.append({"target": alias, "status": "dry-run"})
                continue
            history.reserve(key)
            if message.type == "douyin_sticker":
                send_sticker(message.sticker or "")
            else:
                send_text(message.content or "")
            history.mark_success(key)
            results.append({"target": alias, "status": "sent"})
            logger.info("WebBridge 已发送并确认: %s", alias)
        except Exception as exc:
            logger.exception("WebBridge 对象处理失败: %s", alias)
            results.append({"target": alias, "status": "failed", "error": str(exc)})

    payload = {
        "finished_at": datetime.now().astimezone().isoformat(),
        "dry_run": dry_run,
        "message": control["content"],
        "backend": "webbridge",
        "results": results,
    }
    temporary = log_dir / "result.json.tmp"
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(log_dir / "result.json")
    return 1 if any(item["status"] == "failed" for item in results) else 0



def run_webbridge(control: dict, log_dir: Path, *, dry_run: bool) -> int:
    try:
        return _run_webbridge(control, log_dir, dry_run=dry_run)
    finally:
        deactivate_page()
