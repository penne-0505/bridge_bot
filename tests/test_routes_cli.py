from __future__ import annotations

from bot.bridge.routes_cli import _generate_reciprocals, _validate_routes_payload


def test_generate_reciprocals_adds_missing_reverse():
    routes = [
        {
            "src": {"guild": 1, "channel": 10},
            "dst": {"guild": 2, "channel": 20},
        }
    ]

    result = _generate_reciprocals(routes)

    assert len(result) == 2
    keys = {
        (r["src"]["guild"], r["src"]["channel"], r["dst"]["guild"], r["dst"]["channel"])
        for r in result
    }
    assert (1, 10, 2, 20) in keys
    assert (2, 20, 1, 10) in keys


def test_generate_reciprocals_does_not_duplicate_existing_reverse():
    routes = [
        {
            "src": {"guild": 1, "channel": 10},
            "dst": {"guild": 2, "channel": 20},
        },
        {
            "src": {"guild": 2, "channel": 20},
            "dst": {"guild": 1, "channel": 10},
        },
    ]

    result = _generate_reciprocals(routes)

    # すでに逆方向があるので件数は変わらない
    assert len(result) == 2


def test_validate_routes_payload_uses_loader_for_validation():
    # 正常なルート定義は例外を投げない
    ok_routes = [
        {
            "src": {"guild": 1, "channel": 10},
            "dst": {"guild": 2, "channel": 20},
        }
    ]
    _validate_routes_payload(ok_routes)

    # 不正なルート定義は ValueError になる (guild が 0)
    bad_routes = [
        {
            "src": {"guild": 0, "channel": 10},
            "dst": {"guild": 2, "channel": 20},
        }
    ]
    try:
        _validate_routes_payload(bad_routes)
    except ValueError:
        pass
    else:  # pragma: no cover - 期待した例外が出なかった場合の保険
        raise AssertionError("invalid routes payload must raise ValueError")

