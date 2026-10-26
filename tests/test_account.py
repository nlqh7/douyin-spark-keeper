from __future__ import annotations

import json

import app.account as account


def test_cached_account_and_scan_status(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(account, "DATA_DIR", tmp_path)
    monkeypatch.setattr(account, "ACCOUNT_PATH", tmp_path / "account.json")
    monkeypatch.setattr(account, "SCAN_PATH", tmp_path / "scan-status.json")
    account.ACCOUNT_PATH.write_text(json.dumps({"name": "测试账号"}), encoding="utf-8")
    account.SCAN_PATH.write_text(json.dumps({"count": 2, "targets": ["甲", "乙"]}), encoding="utf-8")
    monkeypatch.setattr(account, "command", lambda *args: (_ for _ in ()).throw(AssertionError("不应访问浏览器")))

    result = account.account_status()

    assert result["account"]["name"] == "测试账号"
    assert result["scan"]["count"] == 2
    assert result["scan"]["targets"] == ["甲", "乙"]


def test_first_account_read_is_cached(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(account, "DATA_DIR", tmp_path)
    monkeypatch.setattr(account, "ACCOUNT_PATH", tmp_path / "account.json")
    monkeypatch.setattr(account, "SCAN_PATH", tmp_path / "scan-status.json")
    calls = []
    monkeypatch.setattr(account, "command", lambda action, args: calls.append((action, args)) or {})
    monkeypatch.setattr(account, "evaluate", lambda code: ["测试账号"])
    monkeypatch.setattr(account, "ensure_chat", lambda: None)

    result = account.account_status()
    second = account.account_status()

    assert result["account"]["name"] == "测试账号"
    assert second["scan"]["count"] is None
    assert len(calls) == 1
