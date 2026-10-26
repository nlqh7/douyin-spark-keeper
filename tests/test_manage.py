from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import manage


def isolated_manage(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(manage, "ROOT", tmp_path)
    monkeypatch.setattr(manage, "VENV_PYTHON", tmp_path / ".venv" / "Scripts" / "python.exe")
    monkeypatch.setattr(manage, "DATA_DIR", tmp_path / "data")
    monkeypatch.setattr(manage, "CONTROL_PATH", tmp_path / "data" / "control.json")
    manage.VENV_PYTHON.parent.mkdir(parents=True)
    manage.VENV_PYTHON.touch()
    manage.DATA_DIR.mkdir()
    (manage.DATA_DIR / "storage-state.json").touch()


def test_resume_creates_only_named_daily_task(monkeypatch, tmp_path) -> None:
    isolated_manage(monkeypatch, tmp_path)
    run = MagicMock(return_value=SimpleNamespace(returncode=0, stdout="", stderr=""))
    monkeypatch.setattr(manage.subprocess, "run", run)

    assert manage.resume() == 0

    create = run.call_args_list[0].args[0]
    assert create[:8] == ["schtasks", "/Create", "/TN", "DouyinSpark23", "/SC", "DAILY", "/ST", "23:00"]
    assert "run --scheduled" in create[create.index("/TR") + 1]
    assert json.loads(manage.CONTROL_PATH.read_text(encoding="utf-8"))["enabled"] is True


def test_pause_disables_schedule_and_send_permission(monkeypatch, tmp_path) -> None:
    isolated_manage(monkeypatch, tmp_path)
    manage.save_control({"enabled": True, "headless": False})
    run = MagicMock(return_value=SimpleNamespace(returncode=0, stdout="", stderr=""))
    monkeypatch.setattr(manage.subprocess, "run", run)

    assert manage.pause() == 0

    run.assert_called_once()
    assert run.call_args.args[0] == ["schtasks", "/Change", "/TN", "DouyinSpark23", "/DISABLE"]
    assert json.loads(manage.CONTROL_PATH.read_text(encoding="utf-8"))["enabled"] is False


def test_uninstall_deletes_only_named_task(monkeypatch, tmp_path) -> None:
    isolated_manage(monkeypatch, tmp_path)
    run = MagicMock(return_value=SimpleNamespace(returncode=0, stdout="", stderr=""))
    monkeypatch.setattr(manage.subprocess, "run", run)

    assert manage.uninstall() == 0

    run.assert_called_once()
    assert run.call_args.args[0] == ["schtasks", "/Delete", "/TN", "DouyinSpark23", "/F"]
    assert json.loads(manage.CONTROL_PATH.read_text(encoding="utf-8"))["enabled"] is False


def test_next_send_time_is_23_and_rolls_to_tomorrow() -> None:
    from datetime import datetime
    from zoneinfo import ZoneInfo

    zone = ZoneInfo("Asia/Shanghai")
    before = datetime(2026, 10, 25, 22, 30, tzinfo=zone)
    after = datetime(2026, 10, 25, 23, 1, tzinfo=zone)

    assert manage.next_send_time(before).isoformat() == "2026-10-25T23:00:00+08:00"
    assert manage.next_send_time(after).isoformat() == "2026-10-26T23:00:00+08:00"
    assert manage.next_send_time(before, "22:45").isoformat() == "2026-10-25T22:45:00+08:00"


def test_configure_persists_time_and_native_sticker(monkeypatch, tmp_path) -> None:
    isolated_manage(monkeypatch, tmp_path)
    args = SimpleNamespace(time="22:45", message_type="sticker", content="晚上好", browser_mode="default")

    assert manage.configure(args) == 0

    saved = json.loads(manage.CONTROL_PATH.read_text(encoding="utf-8"))
    assert saved["time"] == "22:45"
    assert saved["message_type"] == "sticker"
    assert saved["content"] == "晚上好"
    assert saved["enabled"] is False
