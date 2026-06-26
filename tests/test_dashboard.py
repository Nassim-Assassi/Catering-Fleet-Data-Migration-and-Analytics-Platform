import dashboard
import sys
import types

import pandas as pd


class _FakeScale:
    def __init__(self, domain=None):
        self.domain = domain


class _FakeChart:
    pass


class _FakeAltair(types.SimpleNamespace):
    def __init__(self):
        super().__init__(Scale=_FakeScale, Chart=_FakeChart)


class _FakeStreamlit:
    @staticmethod
    def cache_data(ttl=None):
        def decorator(func):
            return func

        return decorator


if "streamlit" not in sys.modules:
    sys.modules["streamlit"] = _FakeStreamlit()

if "awswrangler" not in sys.modules:
    sys.modules["awswrangler"] = types.SimpleNamespace(
        athena=types.SimpleNamespace(
            read_sql_query=lambda **kwargs: pd.DataFrame())
    )

if "altair" not in sys.modules:
    sys.modules["altair"] = _FakeAltair()


class TestGetFormattedMonthYear:
    def test_get_formatted_month_year_returns_readable_label(self):
        result = dashboard.get_formatted_month_year(2026, 6)

        assert result == "June 2026"


class TestGetTruckColourScale:
    def test_get_truck_colour_scale_returns_sorted_domain(self):
        trucks_df = pd.DataFrame(
            {"truck_name": ["Zulu", "Alpha", "Alpha", None]})

        scale = dashboard.get_truck_colour_scale(trucks_df)

        assert scale.domain == ["Alpha", "Zulu"]
