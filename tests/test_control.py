from __future__ import annotations

import pytest

from app.control import message_for_control, normalize_control


def test_defaults_preserve_original_behavior() -> None:
    control = normalize_control({})
    assert control["time"] == "23:00"
    message, stickers = message_for_control(control)
    assert message.type == "text"
    assert message.content == "火"
    assert stickers == {}


def test_custom_text_and_time() -> None:
    control = normalize_control({"time": "22:45", "message_type": "text", "content": "🔥"})
    message, _ = message_for_control(control)
    assert control["time"] == "22:45"
    assert message.content == "🔥"


def test_native_sticker_configuration() -> None:
    control = normalize_control({"message_type": "sticker", "content": "晚上好"})
    message, stickers = message_for_control(control)
    assert message.type == "douyin_sticker"
    assert message.sticker == "晚上好"
    assert stickers["晚上好"].accessible_name == "晚上好"


@pytest.mark.parametrize("time_value", ["24:00", "23:60", "晚上11点", ""])
def test_invalid_time_is_rejected(time_value: str) -> None:
    with pytest.raises(ValueError, match="时间"):
        normalize_control({"time": time_value})


def test_unknown_sticker_is_rejected() -> None:
    with pytest.raises(ValueError, match="不支持"):
        normalize_control({"message_type": "sticker", "content": "任意图片"})
