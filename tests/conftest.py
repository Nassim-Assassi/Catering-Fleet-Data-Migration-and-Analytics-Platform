from pathlib import Path
import sys
import types
from unittest.mock import Mock


ROOT_DIR = Path(__file__).resolve().parent.parent


def _add_path(path: Path) -> None:
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)


_add_path(ROOT_DIR / "pipeline")
_add_path(ROOT_DIR / "dashboard")
_add_path(ROOT_DIR / "report")
_add_path(ROOT_DIR / ".utils")


class _FakeStreamlit:
    @staticmethod
    def cache_data(ttl=None):
        def decorator(func):
            return func

        return decorator


class _FakeAltair(types.SimpleNamespace):
    class Scale:
        def __init__(self, domain=None):
            self.domain = domain

    class Chart:
        pass


if "streamlit" not in sys.modules:
    sys.modules["streamlit"] = _FakeStreamlit()

if "awswrangler" not in sys.modules:
    sys.modules["awswrangler"] = types.SimpleNamespace(
        athena=types.SimpleNamespace(read_sql_query=Mock()),
        s3=types.SimpleNamespace(to_parquet=Mock()),
    )

if "altair" not in sys.modules:
    sys.modules["altair"] = _FakeAltair()
