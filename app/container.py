from __future__ import annotations

import logging
from dataclasses import dataclass

from psycopg_pool import ConnectionPool

from app.config import AppConfig
from app.db import create_connection_pool, ensure_schema
from bot import BridgeBotClient, register_bridge_commands
from bot.bridge import (
    BridgeMessageStore,
    BridgeProfileStore,
    ChannelBridgeManager,
    ChannelRoute,
    load_channel_routes,
)


LOGGER = logging.getLogger(__name__)

@dataclass(slots=True)
class BridgeApplication:
    """BridgeBotClient とトークンを保持し、実行処理を提供する。"""

    client: BridgeBotClient
    token: str
    db_pool: ConnectionPool

    async def run(self) -> None:
        try:
            async with self.client:
                await self.client.start(self.token)
        finally:
            self.db_pool.close()


@dataclass(slots=True)
class _BridgeDependencies:
    profile_store: BridgeProfileStore
    message_store: BridgeMessageStore
    routes: list[ChannelRoute]
    db_pool: ConnectionPool


def _load_bridge_dependencies(config: AppConfig) -> _BridgeDependencies:
    pool = create_connection_pool(config.database_url)
    ensure_schema(pool)
    profile_store = BridgeProfileStore(pool)
    message_store = BridgeMessageStore(pool)
    routes = list(
        load_channel_routes(
            env_enabled=config.bridge_routes_env.enabled,
            env_payload=config.bridge_routes_env.routes_json,
            require_reciprocal=config.bridge_routes_env.require_reciprocal,
            strict=config.bridge_routes_env.strict,
        )
    )
    _log_loaded_routes(routes)
    return _BridgeDependencies(
        profile_store=profile_store,
        message_store=message_store,
        routes=routes,
        db_pool=pool,
    )


async def build_bridge_app(config: AppConfig) -> BridgeApplication:
    bridge_dependencies = _load_bridge_dependencies(config)

    client = BridgeBotClient()
    client.bridge_manager = ChannelBridgeManager(
        client=client,
        profile_store=bridge_dependencies.profile_store,
        message_store=bridge_dependencies.message_store,
        routes=bridge_dependencies.routes,
    )
    await register_bridge_commands(client)
    LOGGER.info("BridgeBotClient の初期化とコマンド登録が完了しました。")

    return BridgeApplication(
        client=client,
        token=config.discord.token,
        db_pool=bridge_dependencies.db_pool,
    )


def _log_loaded_routes(routes: list[ChannelRoute]) -> None:
    if not routes:
        LOGGER.info("起動時に読み込まれたブリッジ設定はありません。")
        return

    description = ", ".join(_describe_route(route) for route in routes)
    LOGGER.info(
        "起動時に %s 件のブリッジ設定を読み込みました: %s",
        len(routes),
        description,
    )


def _describe_route(route: ChannelRoute) -> str:
    return f"{route.src.describe()} -> {route.dst.describe()}"


__all__ = ["BridgeApplication", "build_bridge_app"]
