from __future__ import annotations

import json
import time
from urllib.request import Request, urlopen


BRIDGE_URL = "http://127.0.0.1:10086/command"
SESSION = "spark-keeper"
CHAT_URL = "https://www.douyin.com/chat"


class WebBridgeError(RuntimeError):
    pass


def command(action: str, args: dict | None = None) -> dict:
    body = json.dumps({"action": action, "args": args or {}, "session": SESSION}, ensure_ascii=False).encode("utf-8")
    request = Request(BRIDGE_URL, data=body, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urlopen(request, timeout=45) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except Exception as exc:
        raise WebBridgeError("无法连接 Kimi WebBridge，请确认扩展和本机服务已开启") from exc
    if not payload.get("ok"):
        raise WebBridgeError(str(payload.get("error") or payload))
    data = payload.get("data")
    return data if isinstance(data, dict) else {"value": data}


def evaluate(code: str):
    result = command("evaluate", {"code": code})
    return result.get("value")


def ensure_chat() -> None:
    tabs = command("list_tabs").get("tabs", [])
    if any(tab.get("url", "").startswith(CHAT_URL) for tab in tabs):
        command("find_tab", {"url": CHAT_URL})
    else:
        command("navigate", {"url": CHAT_URL, "newTab": True, "group_title": "火花管家"})
    command("cdp", {"method": "Page.bringToFront", "params": {}})
    time.sleep(3)
    evaluate("(() => { const cancel = document.querySelector('[class*=\"searchSearchInputsearch_cancel\"]'); if (cancel && cancel.offsetParent !== null) { cancel.click(); return true; } return false; })()")
    time.sleep(0.5)
    structure = evaluate(
        "(() => ({login: document.body.innerText.includes('扫码登录'), search: document.querySelectorAll('input[placeholder*=\"搜索\"]').length}))()"
    )
    if structure.get("login"):
        raise WebBridgeError("当前抖音页面需要登录，请在已打开的 Chrome 页面登录后重试")
    if not structure.get("search"):
        raise WebBridgeError("抖音私信页尚未就绪或页面结构已变化")


def deactivate_page() -> None:
    command("cdp", {"method": "Emulation.setFocusEmulationEnabled", "params": {"enabled": False}})


def discover_gray_streaks() -> list[str]:
    result = evaluate(
        """(async () => {
          const list = [...document.querySelectorAll('[class*="conversationConversationListwrapper"]')].find(e => e.getBoundingClientRect().height > 0);
          if (!list) return {conversations: 0, names: []};
          const names = new Set();
          list.scrollTop = 0;
          const wait = ms => new Promise(resolve => setTimeout(resolve, ms));
          await wait(400);
          for (let i = 0; i < 100; i++) {
            list.querySelectorAll('[data-e2e="conversation-item"]:has([class*="commonStreakstreakContainer"] [class*="commonStreakicon"][src*="/gray_"])').forEach(row => {
              const title = row.querySelector('[class*="conversationConversationItemtitle"]');
              const name = title && (title.innerText || title.textContent || '').trim();
              if (name) names.add(name);
            });
            if (list.scrollTop + list.clientHeight >= list.scrollHeight - 2) break;
            list.scrollTop = Math.min(list.scrollTop + Math.max(300, list.clientHeight * .8), list.scrollHeight);
            await wait(350);
          }
          return {conversations: document.querySelectorAll('[data-e2e="conversation-item"]').length, names: [...names]};
        })()"""
    )
    if not result.get("conversations"):
        raise WebBridgeError("未识别到私信会话，无法确认扫描是否有效")
    return result["names"]


def trusted_click(rect: dict) -> None:
    x, y = rect["x"], rect["y"]
    command("cdp", {"method": "Input.dispatchMouseEvent", "params": {"type": "mousePressed", "x": x, "y": y, "button": "left", "clickCount": 1}})
    command("cdp", {"method": "Input.dispatchMouseEvent", "params": {"type": "mouseReleased", "x": x, "y": y, "button": "left", "clickCount": 1}})


def open_target(name: str) -> None:
    encoded = json.dumps(name, ensure_ascii=False)
    rect = evaluate(
        f"""(async () => {{
          const expected = {encoded};
          const list = [...document.querySelectorAll('[class*="conversationConversationListwrapper"]')].find(e => e.getBoundingClientRect().height > 0);
          if (!list) return {{reason: 'no-list'}};
          let matches = 0;
          const wait = ms => new Promise(resolve => setTimeout(resolve, ms));
          list.scrollTop = 0;
          await wait(300);
          for (let i = 0; i < 100; i++) {{
            for (const row of list.querySelectorAll('[data-e2e="conversation-item"]')) {{
              const title = row.querySelector('[class*="conversationConversationItemtitle"]');
              if (title && (title.innerText || title.textContent || '').trim() === expected) {{
                matches += 1;
                list.scrollTop = Math.max(0, row.offsetTop - list.clientHeight / 2);
                await wait(400);
                const bounds = row.getBoundingClientRect();
                if (bounds.width > 0 && bounds.height > 0) return {{x: bounds.x + bounds.width / 2, y: bounds.y + bounds.height / 2}};
              }}
            }}
            if (list.scrollTop + list.clientHeight >= list.scrollHeight - 2) break;
            list.scrollTop = Math.min(list.scrollTop + Math.max(300, list.clientHeight * .8), list.scrollHeight);
            await wait(250);
          }}
          return {{reason: 'not-visible', matches}};
        }})()"""
    )
    if not rect or "x" not in rect:
        raise WebBridgeError(f"无法定位目标会话（名称匹配数: {rect.get('matches', 0) if rect else 0}）")
    before_title = evaluate("(() => (document.querySelector('[class*=\"RightPanelHeadertitle\"]')?.textContent || '').trim())()")
    trusted_click(rect)
    time.sleep(1.5)
    confirmed = evaluate(
        """(() => {
          const title = (document.querySelector('[class*="RightPanelHeadertitle"]')?.textContent || '').trim();
          const composer = document.querySelector('[data-contents="true"], [contenteditable="true"], textarea[placeholder*="消息"]');
          return {title, changed: Boolean(title), composer: Boolean(composer)};
        })()"""
    )
    if not confirmed["changed"] or not confirmed["composer"] or confirmed["title"] == before_title:
        raise WebBridgeError("点击后无法确认右侧会话已切换且输入框可用")


def send_text(content: str) -> None:
    command("fill", {"selector": '[data-contents="true"]', "value": content})
    clicked = evaluate(
        "(() => { const button = document.querySelector('[class*=\"messageMsgInputpublishBtn\"], .e2e-send-msg-bt, button[aria-label*=\"发送\"]'); if (!button) return false; button.click(); return true; })()"
    )
    if not clicked:
        raise WebBridgeError("找不到发送按钮")
    time.sleep(2.5)
    encoded = json.dumps(content, ensure_ascii=False)
    confirmed = evaluate(
        f"""(() => {{
          const latest = document.querySelector('.messageMessageListlist [data-index="0"] .messageMessageBoxmessageBox:has(.messageMessageBoxcontentBox.messageMessageBoxisFromMe)');
          if (!latest) return false;
          const failed = latest.querySelector('[aria-label*="重试"], [title*="重试"], [class*="SendStatusretry"], [class*="ContentSideSendStatusretry"]');
          return !failed && latest.innerText.includes({encoded});
        }})()"""
    )
    if not confirmed:
        raise WebBridgeError("消息触发后无法确认发送结果，为避免重复不会重试")


def send_sticker(name: str) -> None:
    clicked = evaluate(
        "(() => { const button = document.querySelector('svg.messageMsgInputiconAction, button[aria-label*=\"表情\"], [role=\"button\"][aria-label*=\"表情\"]'); if (!button) return false; button.click(); return true; })()"
    )
    if not clicked:
        raise WebBridgeError("找不到表情按钮")
    time.sleep(0.8)
    encoded = json.dumps(name, ensure_ascii=False)
    selected = evaluate(
        f"""(() => {{
          const panels = [...document.querySelectorAll('.componentsemojiemojiPanel, [class*="emojiPanel"], [role="dialog"]')];
          for (const panel of panels) {{
            for (const node of panel.querySelectorAll('[aria-label], [title], img, .emojiEmojiItememojiItemDesc')) {{
              const label = node.getAttribute('aria-label') || node.getAttribute('title') || node.getAttribute('alt') || node.innerText;
              if (label?.trim() === {encoded}) {{ (node.closest('[role="button"]') || node).click(); return true; }}
            }}
          }}
          return false;
        }})()"""
    )
    if not selected:
        raise WebBridgeError(f"表情面板中找不到原生表情：{name}")
    time.sleep(1)
    evaluate(
        "(() => { const button = document.querySelector('[class*=\"messageMsgInputpublishBtn\"], .e2e-send-msg-bt'); if (button) button.click(); return true; })()"
    )
    time.sleep(2.5)
    confirmed = evaluate(
        "(() => { const latest = document.querySelector('.messageMessageListlist [data-index=\"0\"] .messageMessageBoxmessageBox:has(.messageMessageBoxcontentBox.messageMessageBoxisFromMe)'); return Boolean(latest && latest.querySelector('img') && !latest.querySelector('[aria-label*=\"重试\"], [class*=\"SendStatusretry\"]')); })()"
    )
    if not confirmed:
        raise WebBridgeError("表情触发后无法确认发送结果，为避免重复不会重试")
