from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

import discord

from bot.bridge.manager import ChannelBridgeManager
from bot.bridge.messages import BridgeMessageStore
from bot.bridge.profiles import BridgeProfileStore


def _build_manager_fixture() -> tuple[ChannelBridgeManager, dict[str, object]]:
    client = MagicMock(spec=discord.Client)
    client.user = SimpleNamespace(id=999, bot=True)

    target_channel = MagicMock()
    target_channel.id = 555
    target_message = SimpleNamespace(id=2222)
    target_message.add_reaction = AsyncMock()
    target_message.remove_reaction = AsyncMock()
    target_channel.fetch_message = AsyncMock(return_value=target_message)
    client.get_channel.return_value = target_channel

    profile_store = MagicMock(spec=BridgeProfileStore)
    message_store = MagicMock(spec=BridgeMessageStore)

    manager = ChannelBridgeManager(
        client=client,
        profile_store=profile_store,
        message_store=message_store,
        routes=[],
    )

    source_channel = SimpleNamespace(id=123)
    source_guild = SimpleNamespace(id=456)
    source_message = SimpleNamespace(id=1111, guild=source_guild, channel=source_channel)

    target_message_id = 9999
    manager._message_links[source_message.id] = {target_message_id}
    manager._message_links[target_message_id] = {source_message.id}
    manager._message_locations[target_message_id] = (789, target_channel.id)

    reaction = SimpleNamespace(message=source_message, emoji="🔥")

    context = {
        "client": client,
        "target_channel": target_channel,
        "target_message": target_message,
        "reaction": reaction,
        "source_message": source_message,
        "target_message_id": target_message_id,
    }
    return manager, context


@pytest.mark.asyncio
async def test_reaction_sync_waits_for_last_user() -> None:
    manager, context = _build_manager_fixture()
    target_message = context["target_message"]
    reaction = context["reaction"]

    user_a = SimpleNamespace(bot=False, id=1)
    user_b = SimpleNamespace(bot=False, id=2)

    await manager.handle_reaction(reaction, user_a, add=True)
    assert target_message.add_reaction.await_count == 1

    await manager.handle_reaction(reaction, user_b, add=True)
    assert target_message.add_reaction.await_count == 1

    await manager.handle_reaction(reaction, user_a, add=False)
    assert target_message.remove_reaction.await_count == 0

    await manager.handle_reaction(reaction, user_b, add=False)
    target_message.remove_reaction.assert_awaited_once_with(reaction.emoji, context["client"].user)


@pytest.mark.asyncio
async def test_reaction_tracking_clears_on_message_delete() -> None:
    manager, context = _build_manager_fixture()
    reaction = context["reaction"]
    user = SimpleNamespace(bot=False, id=55)

    await manager.handle_reaction(reaction, user, add=True)
    assert manager._reaction_members  # sanity check

    manager._message_store.delete.return_value = True
    manager.handle_message_delete(context["source_message"].id)
    assert manager._reaction_members == {}
