from __future__ import annotations

import json
from unittest.mock import MagicMock

import app.webbridge as webbridge
import app.webbridge_runner as runner


def test_command_uses_local_bridge_and_fixed_session(monkeypatch) -> None:
    response = MagicMock()
    response.read.return_value = b'{"ok":true,"data":{"success":true}}'
    response.__enter__.return_value = response
    response.__exit__.return_value = False
    captured = []

    def fake_urlopen(request, timeout):
        captured.append((request, timeout))
        return response

    monkeypatch.setattr(webbridge, "urlopen", fake_urlopen)

    assert webbridge.command("list_tabs")["success"] is True
    request = captured[0][0]
    assert request.full_url == "http://127.0.0.1:10086/command"
    assert json.loads(request.data)["session"] == "spark-keeper-v2"


def configure_runner(monkeypatch):
    history = MagicMock()
    history.run_date.return_value = "2026-10-26"
    history.contains.return_value = False
    history.key.side_effect = lambda *_args: "key"
    monkeypatch.setattr(runner, "History", MagicMock(return_value=history))
    monkeypatch.setattr(runner, "_configure_logging", lambda *args, **kwargs: None)
    monkeypatch.setattr(runner, "ensure_chat", MagicMock())
    monkeypatch.setattr(runner, "deactivate_page", MagicMock())
    monkeypatch.setattr(runner, "discover_gray_streaks", MagicMock(return_value=["甲", "乙"]))
    monkeypatch.setattr(runner, "open_target", MagicMock())
    monkeypatch.setattr(runner, "send_text", MagicMock())
    monkeypatch.setattr(runner, "send_sticker", MagicMock())
    return history


def test_dry_run_checks_every_target_without_sending(monkeypatch, tmp_path) -> None:
    history = configure_runner(monkeypatch)
    control = {"content": "火", "message_type": "text"}

    assert runner.run_webbridge(control, tmp_path, dry_run=True) == 0

    assert runner.open_target.call_count == 2
    runner.send_text.assert_not_called()
    runner.send_sticker.assert_not_called()
    history.reserve.assert_not_called()


def test_webbridge_sends_configured_text_once_per_target(monkeypatch, tmp_path) -> None:
    history = configure_runner(monkeypatch)
    control = {"content": "🔥", "message_type": "text"}

    assert runner.run_webbridge(control, tmp_path, dry_run=False) == 0

    assert runner.send_text.call_count == 2
    runner.send_text.assert_called_with("🔥")
    assert history.mark_success.call_count == 2
