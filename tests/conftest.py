import asyncio
import inspect
import sys
from pathlib import Path

import pytest

# Ensure project root is on sys.path so local packages are importable when
# tests are executed directly or via pytest.
ROOT = Path(__file__).resolve().parent.parent
root_str = str(ROOT)
if root_str not in sys.path:
    sys.path.insert(0, root_str)


def pytest_configure(config: pytest.Config) -> None:
    # Register the asyncio marker so pytest does not warn when the plugin
    # is unavailable (for example, in environments without dev extras).
    config.addinivalue_line("markers", "asyncio: mark test to run in an event loop")


def pytest_pyfunc_call(pyfuncitem: pytest.Function) -> bool | None:
    """Simple asyncio test runner when pytest-asyncio isn't installed."""
    if not inspect.iscoroutinefunction(pyfuncitem.obj):
        return None

    if pyfuncitem.get_closest_marker("asyncio") is None:
        return None

    testargs = {arg: pyfuncitem.funcargs[arg] for arg in pyfuncitem._fixtureinfo.argnames}
    asyncio.run(pyfuncitem.obj(**testargs))
    return True
