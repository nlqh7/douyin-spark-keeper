from __future__ import annotations

from pathlib import Path
import time

from playwright.async_api import async_playwright

from app.local_browser import find_system_browser
from app.profile_browser import open_default_chrome


DOUYIN_URL = "https://www.douyin.com/"


async def login(destination: Path, browser_mode: str = "isolated") -> None:
    if browser_mode == "default":
        print("将使用电脑默认 Chrome 的登录资料；若启动失败，请先关闭所有 Chrome 窗口。")
        async with open_default_chrome(headless=False) as session:
            page = session.page
            await page.goto(DOUYIN_URL, wait_until="domcontentloaded")
            await _open_login(page)
            await _wait_for_login(session.context, page)
        print("默认 Chrome 已确认登录，后续会直接复用。")
        return

    temporary = destination.with_suffix(".tmp")
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=False, executable_path=find_system_browser())
        context = await browser.new_context(locale="zh-CN")
        page = await context.new_page()
        try:
            await page.goto(DOUYIN_URL, wait_until="domcontentloaded")
            await _open_login(page)
            print("这是工具专用浏览器，不会读取你日常浏览器的登录状态。")
            await _wait_for_login(context, page)
            await context.storage_state(path=temporary)
        finally:
            await browser.close()
    temporary.replace(destination)
    print("登录状态已保存到项目 data 目录。")


async def _wait_for_login(context, page) -> None:
    print("如尚未登录，请扫码；检测到登录状态后会自动关闭窗口。")
    deadline = time.monotonic() + 600
    while True:
        cookies = await context.cookies(DOUYIN_URL)
        if any(cookie.get("name") in {"sessionid", "sessionid_ss"} and cookie.get("value") for cookie in cookies):
            break
        if time.monotonic() >= deadline:
            raise RuntimeError("等待扫码登录超时，请重新运行 login")
        await page.wait_for_timeout(1_000)
    await page.wait_for_timeout(2_000)


async def _open_login(page) -> None:
    login = page.get_by_text("登录", exact=True)
    if await login.count():
        try:
            await login.first.click(timeout=10_000)
        except Exception:
            pass
    qr_login = page.get_by_text("扫码登录", exact=True)
    if await qr_login.count():
        try:
            await qr_login.first.click(timeout=5_000)
        except Exception:
            pass


if __name__ == "__main__":
    raise SystemExit("请通过 python manage.py login 启动")
