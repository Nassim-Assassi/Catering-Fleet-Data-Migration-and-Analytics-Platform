import data_wranglers
import sys
import types
from unittest.mock import Mock

import pandas as pd


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
        athena=types.SimpleNamespace(read_sql_query=Mock())
    )


class TestLoadTotalRevenueForMonth:
    def test_load_total_revenue_for_month_returns_scalar_value(self, monkeypatch):
        mock_read_sql_query = Mock(
            return_value=pd.DataFrame({"total_revenue": [123.45]}))
        monkeypatch.setattr(data_wranglers.wr.athena,
                            "read_sql_query", mock_read_sql_query)

        result = data_wranglers.load_total_revenue_for_month(
            "analytics", 2026, 6)

        assert result == 123.45
        assert "WHERE year = 2026" in mock_read_sql_query.call_args.kwargs["sql"]
        assert "AND month = 6" in mock_read_sql_query.call_args.kwargs["sql"]


class TestLoadTotalSalesPerTruckForMonth:
    def test_load_total_sales_per_truck_for_month_returns_dataframe(self, monkeypatch):
        expected_df = pd.DataFrame({"truck_name": ["A"], "total_sales": [10]})
        mock_read_sql_query = Mock(return_value=expected_df)
        monkeypatch.setattr(data_wranglers.wr.athena,
                            "read_sql_query", mock_read_sql_query)

        result = data_wranglers.load_total_sales_per_truck_for_month(
            "analytics", 2026, 6)

        assert result.equals(expected_df)
