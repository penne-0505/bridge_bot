from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Iterable, List, Sequence, Set, Tuple

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class ChannelEndpoint:
    guild: int
    channel: int

    @classmethod
    def from_payload(cls, payload: dict) -> "ChannelEndpoint":
        guild = int(payload["guild"])
        channel = int(payload["channel"])
        if guild <= 0 or channel <= 0:
            raise ValueError("guild と channel は正の整数で指定してください。")
        return cls(guild=guild, channel=channel)

    def key(self) -> tuple[int, int]:
        return (self.guild, self.channel)


@dataclass(frozen=True, slots=True)
class ChannelRoute:
    src: ChannelEndpoint
    dst: ChannelEndpoint


def load_channel_routes(
    *,
    env_enabled: bool = False,
    env_payload: str | None = None,
    require_reciprocal: bool = False,
    strict: bool = False,
) -> Sequence[ChannelRoute]:
    """Load channel routing configuration from environment variables only."""

    if not env_enabled:
        LOGGER.info(
            "BRIDGE_ROUTES_ENABLED=false のためチャンネルブリッジ設定をロードしません。"
        )
        return ()

    if env_payload is None:
        raise ValueError(
            "BRIDGE_ROUTES_ENABLED=true ですが BRIDGE_ROUTES が未設定です。"
        )

    LOGGER.info(
        "環境変数 BRIDGE_ROUTES を使用してチャンネルブリッジ設定をロードします。"
    )
    try:
        payload: Iterable[dict] = json.loads(env_payload)
    except json.JSONDecodeError as exc:
        raise ValueError("BRIDGE_ROUTES の JSON 解析に失敗しました。") from exc

    routes = _parse_routes_payload(
        payload,
        source="environment",
        require_reciprocal=require_reciprocal,
        strict=strict,
    )
    if routes:
        LOGGER.info(
            "チャンネルブリッジ設定を %s 件ロードしました。(source=environment)",
            len(routes),
        )
    return routes


def _parse_routes_payload(
    payload: Iterable[dict],
    *,
    source: str,
    require_reciprocal: bool,
    strict: bool,
) -> Sequence[ChannelRoute]:
    routes: List[ChannelRoute] = []
    seen_pairs: Set[Tuple[Tuple[int, int], Tuple[int, int]]] = set()

    for entry in payload:
        try:
            src = ChannelEndpoint.from_payload(entry["src"])
            dst = ChannelEndpoint.from_payload(entry["dst"])
        except (KeyError, TypeError, ValueError) as exc:
            message = f"不正なルート定義をスキップしました: entry={entry}, error={exc}"
            if strict:
                raise ValueError(message) from exc
            LOGGER.warning(message)
            continue

        pair_key = (src.key(), dst.key())
        if pair_key in seen_pairs:
            message = f"重複するルート定義をスキップしました: src={src}, dst={dst}"
            if strict:
                raise ValueError(message)
            LOGGER.warning(message)
            continue
        seen_pairs.add(pair_key)

        LOGGER.info("チャンネルブリッジを読み込み: %s -> %s", src, dst)
        routes.append(ChannelRoute(src=src, dst=dst))

    if require_reciprocal:
        pair_lookup = {(route.src.key(), route.dst.key()) for route in routes}
        missing = [
            route
            for route in routes
            if (route.dst.key(), route.src.key()) not in pair_lookup
        ]
        if missing:
            problematic = ", ".join(
                f"{route.src.key()}->{route.dst.key()}" for route in missing
            )
            raise ValueError(
                "BRIDGE_ROUTES_REQUIRE_RECIPROCAL=true が設定されていますが、逆方向ルートが不足しています: "
                + problematic
            )

    return routes


__all__ = ["ChannelEndpoint", "ChannelRoute", "load_channel_routes"]
