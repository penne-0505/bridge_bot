from __future__ import annotations

import asyncio
import logging

from app import build_bridge_app, load_config
from app.diagnostics import log_startup_diagnostics


LOGGER = logging.getLogger(__name__)


async def run_bridge_bot() -> None:
    try:
        config = load_config()
    except Exception:  # pragma: no cover - 設定読み込み失敗は希少
        LOGGER.exception("bridge_base の設定読み込みに失敗しました。")
        return

    log_startup_diagnostics(config)
    app = await build_bridge_app(config)
    await app.run()


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run_bridge_bot())


if __name__ == "__main__":
    LOGGER.info("BridgeBot を起動します。")
    main()
