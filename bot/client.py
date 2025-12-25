from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import discord


if TYPE_CHECKING:
    from bot.bridge import ChannelBridgeManager


LOGGER = logging.getLogger(__name__)


class BridgeBotClient(discord.Client):
    """チャンネルブリッジ専用の Discord クライアント。"""

    def __init__(
        self,
        *,
        intents: discord.Intents | None = None,
        bridge_manager: "ChannelBridgeManager" | None = None,
    ) -> None:
        super().__init__(intents=intents or discord.Intents.all())
        self.tree = discord.app_commands.CommandTree(self)
        self.bridge_manager = bridge_manager

    async def on_ready(self) -> None:
        if self.user is None:
            LOGGER.warning("クライアントユーザー情報を取得できませんでした。")
            return

        LOGGER.info("BridgeBotClient ログイン完了: %s (ID: %s)", self.user, self.user.id)
        if self.bridge_manager is not None:
            try:
                await self.bridge_manager.ensure_guild_colors(self.guilds)
            except Exception as exc:
                LOGGER.warning("ギルドカラーの同期に失敗しました: error=%s", exc)
        await self.tree.sync()
        LOGGER.info("アプリケーションコマンドの同期が完了しました。")
        LOGGER.info("チャンネルブリッジの待機を開始します。")

    async def on_message(self, message: discord.Message) -> None:
        if self.bridge_manager is None:
            return
        await self.bridge_manager.handle_message(message)

    async def on_message_edit(
        self,
        before: discord.Message,
        after: discord.Message,
    ) -> None:
        if self.bridge_manager is None:
            return
        await self.bridge_manager.handle_message_edit(before, after)

    async def on_reaction_add(
        self,
        reaction: discord.Reaction,
        user: discord.abc.User,
    ) -> None:
        if self.bridge_manager is None:
            return
        await self.bridge_manager.handle_reaction(reaction, user, add=True)

    async def on_reaction_remove(
        self,
        reaction: discord.Reaction,
        user: discord.abc.User,
    ) -> None:
        if self.bridge_manager is None:
            return
        await self.bridge_manager.handle_reaction(reaction, user, add=False)

    async def on_message_delete(self, message: discord.Message) -> None:
        if self.bridge_manager is None:
            return
        self.bridge_manager.handle_message_delete(message.id)


__all__ = ["BridgeBotClient"]
