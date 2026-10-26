from __future__ import annotations

import json
import os
from pathlib import Path

from app.webbridge import ensure_chat, evaluate, command


ROOT = Path(os.environ.get("SPARK_ROOT", Path(__file__).resolve().parents[1]))
DATA_DIR = ROOT / "data"
ACCOUNT_PATH = DATA_DIR / "account.json"
SCAN_PATH = DATA_DIR / "scan-status.json"


def account_status() -> dict:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not ACCOUNT_PATH.is_file():
        command("navigate", {"url": "https://www.douyin.com/user/self", "newTab": True, "group_title": "火花账号信息"})
        names = evaluate("(() => [...document.querySelectorAll('h1')].map(e => e.innerText.trim()).filter(Boolean))()")
        if not names:
            raise RuntimeError("无法读取当前抖音账号名称")
        ACCOUNT_PATH.write_text(json.dumps({"name": names[0]}, ensure_ascii=False), encoding="utf-8")
        ensure_chat()
    account = json.loads(ACCOUNT_PATH.read_text(encoding="utf-8"))
    try:
        scan = json.loads(SCAN_PATH.read_text(encoding="utf-8"))
    except FileNotFoundError:
        scan = {"count": None, "targets": []}
    return {"account": account, "scan": scan}
