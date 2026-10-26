from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path

from playwright.async_api import async_playwright

from app.browser import BrowserSession
from app.local_browser import find_system_browser


def default_chrome_profile() -> Path:
    local = os.environ.get("LOCALAPPDATA")
    if not local:
        raise RuntimeError("无法定位电脑默认 Chrome 配置目录")
    path = Path(local) / "Google" / "Chrome" / "User Data"
    if not path.is_dir():
        raise RuntimeError("未找到电脑默认 Chrome 配置目录")
    return path


@asynccontextmanager
async def open_default_chrome(*, headless: bool = False):
    playwright = await async_playwright().start()
    context = None
    try:
        try:
            context = await playwright.chromium.launch_persistent_context(
                user_data_dir=str(default_chrome_profile()),
                executable_path=find_system_browser(),
                headless=headless,
                viewport={"width": 1440, "height": 1000},
                locale="zh-CN",
            )
        except Exception as exc:
            raise RuntimeError("无法打开默认 Chrome 配置。请先关闭所有 Chrome 窗口后重试；若仍失败，请改用独立浏览器模式") from exc
        page = context.pages[0] if context.pages else await context.new_page()
        yield BrowserSession(page=page, context=context)
    finally:
        if context:
            await context.close()
        await playwright.stop()
