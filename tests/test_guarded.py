from __future__ import annotations

from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

import app.guarded as guarded


def configure_run(monkeypatch, friends: list[str]):
    page = MagicMock()
    page.screenshot = AsyncMock()
    session = SimpleNamespace(page=page)

    @asynccontextmanager
    async def fake_open_douyin(_settings):
        yield session

    history = MagicMock()
    history.run_date.return_value = "2026-10-25"
    history.contains.return_value = False
    history.key.side_effect = lambda _task, _date, name, _message: f"key:{name}"
    chat = MagicMock()
    chat.open_target = AsyncMock()
    send = AsyncMock()

    monkeypatch.setattr(guarded, "load_control", lambda: {"enabled": True, "headless": True, "time": "23:00", "message_type": "text", "content": "火", "browser_mode": "isolated"})
    monkeypatch.setattr(guarded, "settings_for_run", MagicMock())
    monkeypatch.setattr(guarded, "open_douyin", fake_open_douyin)
    monkeypatch.setattr(guarded, "open_private_messages", AsyncMock())
    monkeypatch.setattr(guarded, "discover_streak_friends", AsyncMock(return_value=friends))
    monkeypatch.setattr(guarded, "History", MagicMock(return_value=history))
    monkeypatch.setattr(guarded, "DouyinChat", MagicMock(return_value=chat))
    monkeypatch.setattr(guarded, "verify_login", AsyncMock())
    monkeypatch.setattr(guarded, "send_message", send)
    monkeypatch.setattr(guarded, "_configure_logging", lambda *args, **kwargs: None)
    monkeypatch.setattr(guarded, "_write_results", MagicMock())
    return chat, history, send


@pytest.mark.asyncio
async def test_sends_one_fire_to_every_gray_streak(monkeypatch) -> None:
    chat, history, send = configure_run(monkeypatch, ["好友甲", "好友乙"])

    assert await guarded.run_guarded(dry_run=False) == 0

    assert chat.open_target.await_args_list[0].args == ("好友甲",)
    assert chat.open_target.await_args_list[1].args == ("好友乙",)
    assert send.await_count == 2
    for call in send.await_args_list:
        assert call.args[2].type == "text"
        assert call.args[2].content == "火"
    assert history.mark_success.call_count == 2


@pytest.mark.asyncio
async def test_dry_run_never_sends_or_reserves_history(monkeypatch) -> None:
    chat, history, send = configure_run(monkeypatch, ["好友甲", "好友乙"])

    assert await guarded.run_guarded(dry_run=True) == 0

    assert chat.open_target.await_count == 2
    send.assert_not_awaited()
    history.reserve.assert_not_called()
    history.mark_success.assert_not_called()


@pytest.mark.asyncio
async def test_existing_history_skips_uncertain_or_completed_target(monkeypatch) -> None:
    chat, history, send = configure_run(monkeypatch, ["好友甲"])
    history.contains.return_value = True

    assert await guarded.run_guarded(dry_run=False) == 0

    chat.open_target.assert_not_awaited()
    send.assert_not_awaited()


@pytest.mark.asyncio
async def test_scheduled_run_requires_explicit_enable(monkeypatch) -> None:
    monkeypatch.setattr(guarded, "load_control", lambda: {"enabled": False})

    with pytest.raises(ValueError, match="尚未启用"):
        await guarded.run_guarded(dry_run=False, scheduled=True)


def test_cleanup_removes_old_screenshots_and_rotates_large_log(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(guarded, "LOG_DIR", tmp_path)
    screenshots = tmp_path / "screenshots"
    screenshots.mkdir()
    old = screenshots / "old.png"
    old.touch()
    old_time = 1_000_000
    import os
    os.utime(old, (old_time, old_time))
    recent = screenshots / "recent.png"
    recent.touch()
    (tmp_path / "run.log").write_bytes(b"x" * (5 * 1024 * 1024 + 1))

    guarded.cleanup_artifacts(now=old_time + 15 * 24 * 60 * 60)

    assert not old.exists()
    assert recent.exists()
    assert (tmp_path / "run.log.1").stat().st_size == 5 * 1024 * 1024 + 1
    assert not (tmp_path / "run.log").exists()
