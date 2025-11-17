from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum, auto
from pathlib import Path
from typing import Callable, Sequence

import psycopg

from app.config import AppConfig
from bot.bridge.routes import ChannelRoute, load_channel_routes


LOGGER = logging.getLogger(__name__)


class DiagnosticStatus(Enum):
    OK = auto()
    WARNING = auto()
    ERROR = auto()


@dataclass(frozen=True, slots=True)
class DiagnosticResult:
    name: str
    status: DiagnosticStatus
    detail: str


DatabaseProbe = Callable[[str], None]


def _default_database_probe(conninfo: str) -> None:
    with psycopg.connect(conninfo=conninfo, connect_timeout=5) as conn:  # type: ignore[arg-type]
        with conn.cursor() as cur:
            cur.execute("SELECT 1")


class StartupDiagnostics:
    """Run health checks before launching the Discord bot."""

    def __init__(
        self,
        *,
        config: AppConfig,
        data_dir: Path | None = None,
        database_probe: DatabaseProbe | None = None,
    ) -> None:
        self._config = config
        base_dir = Path(__file__).resolve().parent.parent
        self._data_dir = Path(data_dir) if data_dir is not None else base_dir / "data"
        self._database_probe = database_probe or _default_database_probe

    def run(self) -> list[DiagnosticResult]:
        results = [
            self._check_discord_token(),
            self._check_database_connectivity(),
            self._check_data_directory(),
            self._check_bridge_routes(),
        ]
        return results

    def _check_discord_token(self) -> DiagnosticResult:
        token_length = len(self._config.discord.token)
        detail = f"DISCORD_BOT_TOKEN を検出しました (length={token_length})."
        return DiagnosticResult(
            name="Discord トークン",
            status=DiagnosticStatus.OK,
            detail=detail,
        )

    def _check_database_connectivity(self) -> DiagnosticResult:
        try:
            self._database_probe(self._config.database_url)
        except Exception as exc:  # pragma: no cover - 実際の接続失敗を記録
            return DiagnosticResult(
                name="PostgreSQL 接続",
                status=DiagnosticStatus.ERROR,
                detail=f"DATABASE_URL への接続に失敗しました: {exc}",
            )

        return DiagnosticResult(
            name="PostgreSQL 接続",
            status=DiagnosticStatus.OK,
            detail="DATABASE_URL への接続確認に成功しました。",
        )

    def _check_data_directory(self) -> DiagnosticResult:
        probe_file = self._data_dir / ".bridge_bot_diag"
        try:
            self._data_dir.mkdir(parents=True, exist_ok=True)
            probe_file.write_text("ok", encoding="utf-8")
            probe_file.unlink(missing_ok=True)
        except OSError as exc:
            return DiagnosticResult(
                name="データディレクトリ",
                status=DiagnosticStatus.ERROR,
                detail=f"{self._data_dir} に書き込みできません: {exc}",
            )

        return DiagnosticResult(
            name="データディレクトリ",
            status=DiagnosticStatus.OK,
            detail=f"{self._data_dir} への読み書きチェックに成功しました。",
        )

    def _check_bridge_routes(self) -> DiagnosticResult:
        settings = self._config.bridge_routes_env
        if not settings.enabled:
            return DiagnosticResult(
                name="ブリッジルート",
                status=DiagnosticStatus.OK,
                detail="BRIDGE_ROUTES_ENABLED=false のためルート同期は無効化されています。",
            )

        if settings.routes_json is None:
            return DiagnosticResult(
                name="ブリッジルート",
                status=DiagnosticStatus.ERROR,
                detail="BRIDGE_ROUTES_ENABLED=true ですが BRIDGE_ROUTES が未設定です。",
            )

        try:
            routes = self._load_routes_from_env(settings.routes_json)
        except Exception as exc:
            return DiagnosticResult(
                name="ブリッジルート",
                status=DiagnosticStatus.ERROR,
                detail=f"環境変数 BRIDGE_ROUTES の検証に失敗しました: {exc}",
            )

        return DiagnosticResult(
            name="ブリッジルート",
            status=DiagnosticStatus.OK,
            detail=f"環境変数から {len(routes)} 件のルート設定を読み込みます。",
        )

    def _load_routes_from_env(self, payload: str) -> Sequence[ChannelRoute]:
        return load_channel_routes(
            env_enabled=True,
            env_payload=payload,
            require_reciprocal=self._config.bridge_routes_env.require_reciprocal,
            strict=self._config.bridge_routes_env.strict,
        )


def log_startup_diagnostics(
    config: AppConfig,
    *,
    data_dir: Path | None = None,
    database_probe: DatabaseProbe | None = None,
) -> list[DiagnosticResult]:
    runner = StartupDiagnostics(
        config=config,
        data_dir=data_dir,
        database_probe=database_probe,
    )
    results = runner.run()

    LOGGER.info("=== BridgeBot 起動前診断 ===")
    for result in results:
        level = _log_level_for_status(result.status)
        LOGGER.log(level, "[%s] %s", result.name, result.detail)

    ok_count = sum(1 for result in results if result.status is DiagnosticStatus.OK)
    LOGGER.info(
        "=== 起動前診断完了: OK %s / %s (warning=%s, error=%s) ===",
        ok_count,
        len(results),
        sum(1 for result in results if result.status is DiagnosticStatus.WARNING),
        sum(1 for result in results if result.status is DiagnosticStatus.ERROR),
    )

    return results


def _log_level_for_status(status: DiagnosticStatus) -> int:
    if status is DiagnosticStatus.ERROR:
        return logging.ERROR
    if status is DiagnosticStatus.WARNING:
        return logging.WARNING
    return logging.INFO


__all__ = [
    "DiagnosticResult",
    "DiagnosticStatus",
    "StartupDiagnostics",
    "log_startup_diagnostics",
]
