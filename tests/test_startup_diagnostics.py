from __future__ import annotations

import json
from typing import Callable

from supabase import Client

from app.config import (
    AppConfig,
    BridgeRouteEnvSettings,
    DiscordSettings,
    SupabaseSettings,
)
from app.diagnostics import DiagnosticStatus, StartupDiagnostics


def _config(
    *,
    routes_env: BridgeRouteEnvSettings | None = None,
) -> AppConfig:
    return AppConfig(
        discord=DiscordSettings(token="dummy-token-value"),
        supabase=SupabaseSettings(
            url="https://example.supabase.co",
            service_role_key="service-role-key",
        ),
        bridge_routes_env=routes_env
        or BridgeRouteEnvSettings(
            enabled=False,
            routes_json=None,
            require_reciprocal=False,
            strict=False,
        ),
    )


def _run_diags(
    config: AppConfig,
    tmp_path,
    *,
    database_probe: Callable[[Client], None] | None = None,
):
    runner = StartupDiagnostics(
        config=config,
        data_dir=tmp_path,
        database_probe=database_probe or (lambda _: None),
    )
    return {result.name: result for result in runner.run()}


def test_startup_diagnostics_ok_when_routes_disabled(tmp_path):
    results = _run_diags(_config(), tmp_path)

    assert results["Discord トークン"].status is DiagnosticStatus.OK
    assert results["Supabase 接続"].status is DiagnosticStatus.OK
    assert results["データディレクトリ"].status is DiagnosticStatus.OK
    assert results["ブリッジルート"].status is DiagnosticStatus.OK


def test_startup_diagnostics_success_with_env_routes(tmp_path):
    routes_env = BridgeRouteEnvSettings(
        enabled=True,
        routes_json=json.dumps(
            [
                {
                    "src": {"guild": 1, "channel": 10},
                    "dst": {"guild": 2, "channel": 20},
                }
            ]
        ),
        require_reciprocal=False,
        strict=False,
    )
    config = _config(routes_env=routes_env)

    results = _run_diags(config, tmp_path)

    assert results["ブリッジルート"].status is DiagnosticStatus.OK


def test_startup_diagnostics_reports_env_payload_error(tmp_path):
    routes_env = BridgeRouteEnvSettings(
        enabled=True,
        routes_json="{",
        require_reciprocal=False,
        strict=False,
    )
    config = _config(routes_env=routes_env)

    results = _run_diags(config, tmp_path)

    assert results["ブリッジルート"].status is DiagnosticStatus.ERROR


def test_startup_diagnostics_reports_database_error(tmp_path):
    config = _config()

    def failing_probe(_: Client) -> None:  # noqa: D401
        raise RuntimeError("boom")

    results = _run_diags(config, tmp_path, database_probe=failing_probe)

    assert results["Supabase 接続"].status is DiagnosticStatus.ERROR
