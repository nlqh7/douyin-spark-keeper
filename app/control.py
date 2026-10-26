from __future__ import annotations

import re

from app.models import Message, Sticker


DEFAULT_CONTROL = {
    "enabled": False,
    "headless": False,
    "time": "23:00",
    "message_type": "text",
    "content": "火",
    "browser_mode": "webbridge",
}
STICKER_NAMES = {"续火花", "晚上好", "比心", "早上好", "早点睡", "在干嘛", "开心", "嗨", "爱心", "绝了", "笑死", "已阅"}


def normalize_control(value: object) -> dict:
    if not isinstance(value, dict) or not isinstance(value.get("enabled", False), bool):
        raise ValueError("data/control.json 配置无效")
    control = {**DEFAULT_CONTROL, **value}
    time_value = control.get("time")
    if not isinstance(time_value, str) or not re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d", time_value):
        raise ValueError("执行时间必须是有效的 HH:MM")
    message_type = control.get("message_type")
    content = control.get("content")
    if message_type not in {"text", "sticker"}:
        raise ValueError("消息类型必须是 text 或 sticker")
    if not isinstance(content, str) or not content.strip() or len(content.strip()) > 20 or "\n" in content or "\r" in content:
        raise ValueError("发送内容必须为 1-20 个字符的单行文本")
    control["content"] = content.strip()
    if message_type == "sticker" and control["content"] not in STICKER_NAMES:
        raise ValueError("不支持这个原生表情，请从本地表情面板中选择")
    if control.get("browser_mode") not in {"webbridge", "isolated", "default"}:
        raise ValueError("浏览器模式必须是 webbridge、isolated 或 default")
    return control


def message_for_control(control: dict) -> tuple[Message, dict[str, Sticker]]:
    if control["message_type"] == "sticker":
        name = control["content"]
        return Message(type="douyin_sticker", sticker=name), {name: Sticker(name=name, accessible_name=name)}
    return Message(type="text", content=control["content"]), {}
