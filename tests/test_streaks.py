from __future__ import annotations

from typing import Any

import pytest

from app.streaks import (
    CONVERSATION_LIST,
    CONVERSATION_ROWS,
    CONVERSATION_TITLE,
    STREAK_CONVERSATIONS,
    UNLIT_STREAK_CONVERSATIONS,
    StreakDiscoveryError,
    discover_streak_friends,
)


class FakeLocator:
    def __init__(self, names: list[str] | None = None) -> None:
        self.names = names or []
        self.first = self

    async def wait_for(self, *, state: str, timeout: int) -> None:
        assert state == "visible"
        assert timeout == 15_000

    async def evaluate(self, script: str) -> Any:
        if "scrollTop = 0" in script:
            return None
        if "top: element.scrollTop" in script:
            return {"top": 0, "height": 100, "client": 100}
        return None

    async def count(self) -> int:
        return len(self.names)

    def nth(self, index: int) -> FakeRow:
        return FakeRow(self.names[index])


class FakeRow:
    def __init__(self, name: str) -> None:
        self.name = name
        self.first = self

    def locator(self, selector: str) -> FakeRow:
        assert selector == CONVERSATION_TITLE
        return self

    async def count(self) -> int:
        return 1

    async def inner_text(self) -> str:
        return self.name


class FakePage:
    def __init__(self, gray_names: list[str], conversation_names: list[str] | None = None) -> None:
        self.conversation_list = FakeLocator()
        self.gray_rows = FakeLocator(gray_names)
        self.conversation_rows = FakeLocator(conversation_names if conversation_names is not None else gray_names)
        self.selectors: list[str] = []

    def locator(self, selector: str) -> FakeLocator:
        self.selectors.append(selector)
        if selector == CONVERSATION_LIST:
            return self.conversation_list
        if selector == CONVERSATION_ROWS:
            return self.conversation_rows
        return self.gray_rows

    async def wait_for_timeout(self, _: int) -> None:
        return None


@pytest.mark.asyncio
async def test_discovers_unique_streak_friend_names() -> None:
    page = FakePage(["好友甲", "好友甲", "好友乙"])

    names = await discover_streak_friends(page)

    assert names == ["好友甲", "好友乙"]
    assert STREAK_CONVERSATIONS in page.selectors


@pytest.mark.asyncio
async def test_limits_discovery_to_unlit_streaks() -> None:
    page = FakePage(["好友甲"])

    assert await discover_streak_friends(page, needs_renewal_only=True) == ["好友甲"]
    assert UNLIT_STREAK_CONVERSATIONS in page.selectors


@pytest.mark.asyncio
async def test_no_conversations_is_unknown_not_successful_empty_scan() -> None:
    page = FakePage([], conversation_names=[])

    with pytest.raises(StreakDiscoveryError, match="无法确认"):
        await discover_streak_friends(page, needs_renewal_only=True)
