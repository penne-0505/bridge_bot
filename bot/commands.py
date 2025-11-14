from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Dict, Iterable, Tuple

import discord

from bot.bridge.routes import ChannelEndpoint, ChannelRoute


LOGGER = logging.getLogger(__name__)


async def register_bridge_commands(client: "BridgeBotClient") -> None:
    """BridgeBotClient にブリッジ関連のコマンドを登録する。"""

    tree = client.tree

    @tree.command(
        name="bridge_links",
        description="このギルドに設定されているチャンネルブリッジを表示します。",
    )
    async def bridge_links(interaction: discord.Interaction) -> None:  # noqa: ANN001
        if interaction.guild is None:
            await _send_ephemeral(
                interaction,
                "このコマンドはサーバー内でのみ使用できます。",
            )
            return

        manager = client.bridge_manager
        if manager is None:
            await _send_ephemeral(
                interaction,
                "チャンネルブリッジ機能が有効になっていません。",
            )
            return

        routes = manager.get_routes_from_guild(interaction.guild.id)
        if not routes:
            await _send_ephemeral(
                interaction,
                "このギルドにはブリッジ連携が設定されていません。",
            )
            return

        await interaction.response.defer(ephemeral=True)

        formatter = _BridgeRouteFormatter(client=client, guild=interaction.guild)
        lines = await formatter.describe_routes(routes)
        message = "🔗 設定されているチャンネルブリッジ\n" + "\n".join(lines)
        await interaction.followup.send(message, ephemeral=True)


@dataclass(slots=True)
class _BridgeRouteFormatter:
    client: "BridgeBotClient"
    guild: discord.Guild
    _cache: Dict[Tuple[int, int], Tuple[str, str]] = field(default_factory=dict)

    async def describe_routes(self, routes: Iterable[ChannelRoute]) -> list[str]:
        lines: list[str] = []
        for index, route in enumerate(routes, start=1):
            src_guild_label, src_channel_label = await self._describe_endpoint(route.src)
            dst_guild_label, dst_channel_label = await self._describe_endpoint(route.dst)
            lines.append(
                f"{index}. 実行元: {src_guild_label} / {src_channel_label}\n"
                f"   連携先: {dst_guild_label} / {dst_channel_label}"
            )
        return lines

    async def _describe_endpoint(self, endpoint: ChannelEndpoint) -> Tuple[str, str]:
        cache_key = (endpoint.guild, endpoint.channel)
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached

        endpoint_guild = await self._resolve_guild(endpoint.guild)
        if endpoint_guild is not None:
            guild_label = f"{endpoint_guild.name} (ID: {endpoint_guild.id})"
            channel_obj: discord.abc.GuildChannel | discord.Thread | None = (
                endpoint_guild.get_channel(endpoint.channel)
            )
        else:
            guild_label = f"(取得失敗: Guild ID {endpoint.guild})"
            channel_obj = None

        if channel_obj is None:
            channel_obj = await self._resolve_channel(endpoint.channel)

        if isinstance(channel_obj, discord.Thread):
            channel_label = f"{channel_obj.name} (Thread, ID: {channel_obj.id})"
        elif isinstance(channel_obj, discord.abc.GuildChannel):
            channel_label = f"{channel_obj.name} (ID: {channel_obj.id})"
        else:
            channel_label = f"(取得失敗: Channel ID {endpoint.channel})"

        value = (guild_label, channel_label)
        self._cache[cache_key] = value
        return value

    async def _resolve_guild(self, guild_id: int) -> discord.Guild | None:
        if guild_id == self.guild.id:
            return self.guild

        guild = self.client.get_guild(guild_id)
        if guild is not None:
            return guild

        try:
            return await self.client.fetch_guild(guild_id)
        except discord.HTTPException as exc:
            LOGGER.warning("ギルドの取得に失敗しました: guild=%s, error=%s", guild_id, exc)
            return None

    async def _resolve_channel(
        self,
        channel_id: int,
    ) -> discord.abc.GuildChannel | discord.Thread | None:
        channel = self.client.get_channel(channel_id)
        if isinstance(channel, (discord.abc.GuildChannel, discord.Thread)):
            return channel

        try:
            fetched = await self.client.fetch_channel(channel_id)
        except discord.HTTPException as exc:
            LOGGER.warning(
                "チャンネルの取得に失敗しました: channel=%s, error=%s",
                channel_id,
                exc,
            )
            return None

        if isinstance(fetched, (discord.abc.GuildChannel, discord.Thread)):
            return fetched

        return None


async def _send_ephemeral(interaction: discord.Interaction, message: str) -> None:
    if interaction.response.is_done():
        await interaction.followup.send(message, ephemeral=True)
    else:
        await interaction.response.send_message(message, ephemeral=True)


__all__ = ["register_bridge_commands"]
