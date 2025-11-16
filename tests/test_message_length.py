from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import discord
import pytest

from bot.bridge.manager import ChannelBridgeManager
from bot.bridge.messages import BridgeMessageStore
from bot.bridge.profiles import BridgeProfile, BridgeProfileStore


def _build_manager_fixture() -> tuple[ChannelBridgeManager, dict[str, object]]:
    client = MagicMock(spec=discord.Client)
    client.user = SimpleNamespace(id=999, bot=True)
    profile_store = MagicMock(spec=BridgeProfileStore)
    message_store = MagicMock(spec=BridgeMessageStore)
    manager = ChannelBridgeManager(
        client=client,
        profile_store=profile_store,
        message_store=message_store,
        routes=[],
    )
    profile = BridgeProfile(
        seed="test",
        display_name="test",
        avatar_url="test",
    )
    context = {
        "client": client,
        "profile": profile,
    }
    return manager, context


@pytest.mark.asyncio
async def test_message_length_limit_with_annotations() -> None:
    manager, context = _build_manager_fixture()
    profile = context["profile"]
    content = "a" * 4096
    # This should fail because the total length will be 4096 + 1 + 11 = 4108
    embed, content_text = manager._compose_mirror_texts(
        raw_content=content,
        annotations=["(annotation)"],
        profile=profile,
    )
    assert embed is not None
    assert len(embed.description) <= 4096
