from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, List, Sequence

from .routes import load_channel_routes


@dataclass(slots=True)
class RouteInput:
    src_guild: int
    src_channel: int
    src_guild_name: str | None
    src_channel_name: str | None
    dst_guild: int
    dst_channel: int
    dst_guild_name: str | None
    dst_channel_name: str | None


def _prompt_positive_int(prompt: str) -> int:
    while True:
        raw = input(prompt).strip()
        if not raw:
            print("値を入力してください。")
            continue
        try:
            value = int(raw)
        except ValueError:
            print("整数で入力してください。")
            continue
        if value <= 0:
            print("1 以上の整数で入力してください。")
            continue
        return value


def _prompt_optional_str(prompt: str) -> str | None:
    raw = input(prompt).strip()
    return raw or None


def _prompt_yes_no(prompt: str, *, default: bool) -> bool:
    suffix = "[Y/n]" if default else "[y/N]"
    while True:
        raw = input(f"{prompt} {suffix} ").strip().lower()
        if not raw:
            return default
        if raw in {"y", "yes"}:
            return True
        if raw in {"n", "no"}:
            return False
        print("y または n で回答してください。")


def _build_route_dict(route: RouteInput) -> dict[str, Any]:
    src: dict[str, Any] = {
        "guild": route.src_guild,
        "channel": route.src_channel,
    }
    if route.src_guild_name is not None:
        src["guild_name"] = route.src_guild_name
    if route.src_channel_name is not None:
        src["channel_name"] = route.src_channel_name

    dst: dict[str, Any] = {
        "guild": route.dst_guild,
        "channel": route.dst_channel,
    }
    if route.dst_guild_name is not None:
        dst["guild_name"] = route.dst_guild_name
    if route.dst_channel_name is not None:
        dst["channel_name"] = route.dst_channel_name

    return {"src": src, "dst": dst}


def _generate_reciprocals(routes: List[dict[str, Any]]) -> List[dict[str, Any]]:
    """与えられたルートに対して、存在しない逆方向ルートを自動生成する。"""

    def _endpoint_key(endpoint: dict[str, Any]) -> tuple[int, int]:
        return int(endpoint["guild"]), int(endpoint["channel"])

    existing_pairs = {
        (_endpoint_key(route["src"]), _endpoint_key(route["dst"])) for route in routes
    }
    generated_pairs: set[tuple[tuple[int, int], tuple[int, int]]] = set()
    new_routes: List[dict[str, Any]] = []

    for route in routes:
        src = route["src"]
        dst = route["dst"]
        src_key = _endpoint_key(src)
        dst_key = _endpoint_key(dst)
        reverse_key = (dst_key, src_key)

        if reverse_key in existing_pairs or reverse_key in generated_pairs:
            continue

        reciprocal = {
            "src": dict(dst),
            "dst": dict(src),
        }
        new_routes.append(reciprocal)
        pair = (src_key, dst_key)
        generated_pairs.add(pair)
        generated_pairs.add(reverse_key)

    return [*routes, *new_routes]


def _validate_routes_payload(routes: Sequence[dict[str, Any]]) -> None:
    payload = json.dumps(routes, ensure_ascii=False)
    # strict=True にすることで CLI 生成結果と実際のローダーの仕様差分を早期に検知する
    load_channel_routes(
        env_enabled=True,
        env_payload=payload,
        require_reciprocal=False,
        strict=True,
    )


def _interactive_build() -> list[dict[str, Any]]:
    print("=== BridgeBot チャンネルルート構築 CLI ===")
    print("このツールは BRIDGE_ROUTES に設定する JSON を対話的に生成します。")
    print("Discord のギルド ID とチャンネル ID は整数 (スノーフレーク) で入力してください。")
    print("ラベル用の guild_name / channel_name は省略できます。空 Enter でスキップします。")

    routes_input: list[RouteInput] = []
    index = 1

    while True:
        print()
        print(f"[ルート {index}]")
        src_guild = _prompt_positive_int("  src.guild (ブリッジ元ギルドID): ")
        src_channel = _prompt_positive_int("  src.channel (ブリッジ元チャンネルID): ")
        src_guild_name = _prompt_optional_str(
            "  src.guild_name (任意 / 運用用ラベル、未入力でスキップ): "
        )
        src_channel_name = _prompt_optional_str(
            "  src.channel_name (任意 / 運用用ラベル、未入力でスキップ): "
        )

        dst_guild = _prompt_positive_int("  dst.guild (ブリッジ先ギルドID): ")
        dst_channel = _prompt_positive_int("  dst.channel (ブリッジ先チャンネルID): ")
        dst_guild_name = _prompt_optional_str(
            "  dst.guild_name (任意 / 運用用ラベル、未入力でスキップ): "
        )
        dst_channel_name = _prompt_optional_str(
            "  dst.channel_name (任意 / 運用用ラベル、未入力でスキップ): "
        )

        routes_input.append(
            RouteInput(
                src_guild=src_guild,
                src_channel=src_channel,
                src_guild_name=src_guild_name,
                src_channel_name=src_channel_name,
                dst_guild=dst_guild,
                dst_channel=dst_channel,
                dst_guild_name=dst_guild_name,
                dst_channel_name=dst_channel_name,
            )
        )

        index += 1
        if not _prompt_yes_no("さらにルートを追加しますか？", default=False):
            break

    if not routes_input:
        raise SystemExit("ルートが1件も定義されていません。処理を中断します。")

    routes = [_build_route_dict(route) for route in routes_input]

    if _prompt_yes_no(
        "BRIDGE_ROUTES_REQUIRE_RECIPROCAL=true を使う予定ですか？ "
        "不足している逆方向ルートを自動生成しますか？",
        default=False,
    ):
        routes = _generate_reciprocals(routes)

    return routes


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="bridge-routes-cli",
        description=(
            "BridgeBot 用の BRIDGE_ROUTES JSON を対話的に構築し、"
            "channel_routes.json に書き出す CLI です。"
        ),
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path("channel_routes.json"),
        help="出力する JSON ファイルパス (既定: ./channel_routes.json)",
    )
    parser.add_argument(
        "--no-validate",
        action="store_true",
        help="生成した JSON を load_channel_routes で事前検証せずに出力します。",
    )

    args = parser.parse_args(list(argv) if argv is not None else None)

    routes = _interactive_build()

    if not args.no_validate:
        try:
            _validate_routes_payload(routes)
        except Exception as exc:
            print()
            print("[ERROR] 生成したルート定義の検証に失敗しました。")
            print(f"詳細: {exc}")
            print("入力値を見直してから再度実行してください。")
            return 1

    output_text = json.dumps(routes, indent=2, ensure_ascii=False)
    args.output.write_text(output_text, encoding="utf-8")

    print()
    print(f"[OK] {args.output} に {len(routes)} 件のルートを書き出しました。")
    print()

    one_line = json.dumps(routes, separators=(",", ":"), ensure_ascii=False)
    print("BRIDGE_ROUTES に設定する JSON (単一行) の例:")
    print(one_line)
    print()
    print("例 (bash):")
    print(f"  export BRIDGE_ROUTES='{one_line}'")
    print("例 (fish):")
    print(f"  set -x BRIDGE_ROUTES '{one_line}'")

    return 0


if __name__ == "__main__":  # pragma: no cover - CLI 直実行用
    raise SystemExit(main())

