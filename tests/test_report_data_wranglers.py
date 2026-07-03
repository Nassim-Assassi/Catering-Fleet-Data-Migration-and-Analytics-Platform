"""Unit tests for report/report_data_wranglers.py."""

import sys
import types
from datetime import date
from unittest.mock import Mock

import pandas as pd
import pytest


if "awswrangler" not in sys.modules:
    sys.modules["awswrangler"] = types.SimpleNamespace(
        athena=types.SimpleNamespace(read_sql_query=Mock())
    )

import report_data_wranglers as data_wranglers


class TestLoadPreviousDayFleetMetrics:
    def test_returns_metrics_from_query(self, monkeypatch):
        mock_read_sql_query = Mock(return_value=pd.DataFrame(
            {"total_revenue": [500.0], "fleet_sales": [20]}))
        monkeypatch.setattr(data_wranglers.wr.athena,
                            "read_sql_query", mock_read_sql_query)

        result = data_wranglers.load_previous_day_fleet_metrics(
            "analytics", "s3://bucket/", date(2026, 7, 2))

        assert result == {"fleet_revenue": 500.0, "fleet_sales": 20}

    def test_returns_zero_defaults_when_query_is_empty(self, monkeypatch):
        mock_read_sql_query = Mock(return_value=pd.DataFrame())
        monkeypatch.setattr(data_wranglers.wr.athena,
                            "read_sql_query", mock_read_sql_query)

        result = data_wranglers.load_previous_day_fleet_metrics(
            "analytics", "s3://bucket/", date(2026, 7, 2))

        assert result == {"fleet_revenue": 0.0, "fleet_sales": 0}


class TestLoadPreviousDayTruckMetrics:
    def test_returns_dataframe_from_query(self, monkeypatch):
        expected_df = pd.DataFrame(
            {"truck_id": [1], "truck_name": ["Alpha"], "revenue": [100.0]})
        mock_read_sql_query = Mock(return_value=expected_df)
        monkeypatch.setattr(data_wranglers.wr.athena,
                            "read_sql_query", mock_read_sql_query)

        result = data_wranglers.load_previous_day_truck_metrics(
            "analytics", "s3://bucket/", date(2026, 7, 2))

        assert result.equals(expected_df)


class TestLoadDailyTruckMetrics:
    def test_returns_dataframe_from_query(self, monkeypatch):
        expected_df = pd.DataFrame(
            {"truck_id": [1], "tx_date": ["2026-07-01"], "revenue": [80.0]})
        mock_read_sql_query = Mock(return_value=expected_df)
        monkeypatch.setattr(data_wranglers.wr.athena,
                            "read_sql_query", mock_read_sql_query)

        result = data_wranglers.load_daily_truck_metrics(
            "analytics", "s3://bucket/", date(2026, 7, 2))

        assert result.equals(expected_df)


class TestLoadExpectedActiveTrucks:
    def test_returns_dataframe_from_query(self, monkeypatch):
        expected_df = pd.DataFrame(
            {"truck_id": [1, 2], "truck_name": ["Alpha", "Beta"]})
        mock_read_sql_query = Mock(return_value=expected_df)
        monkeypatch.setattr(data_wranglers.wr.athena,
                            "read_sql_query", mock_read_sql_query)

        result = data_wranglers.load_expected_active_trucks(
            "analytics", "s3://bucket/")

        assert result.equals(expected_df)


class TestSafePctChange:
    def test_returns_percent_increase(self):
        result = data_wranglers._safe_pct_change(120.0, 100.0)

        assert result == 20.0

    def test_returns_percent_decrease(self):
        result = data_wranglers._safe_pct_change(50.0, 100.0)

        assert result == -50.0

    def test_returns_none_when_reference_is_zero(self):
        result = data_wranglers._safe_pct_change(50.0, 0.0)

        assert result is None


class TestBaselineFlag:
    def test_returns_na_when_baseline_is_zero(self):
        row = pd.Series({"baseline_mean_revenue": 0.0, "revenue": 100.0})

        result = data_wranglers._baseline_flag(row)

        assert result == "na"

    def test_returns_overperforming_when_revenue_is_high(self):
        row = pd.Series({"baseline_mean_revenue": 100.0, "revenue": 140.0})

        result = data_wranglers._baseline_flag(row)

        assert result == "overperforming"

    def test_returns_underperformer_when_revenue_is_low(self):
        row = pd.Series({"baseline_mean_revenue": 100.0, "revenue": 60.0})

        result = data_wranglers._baseline_flag(row)

        assert result == "underperformer"

    def test_returns_neutral_otherwise(self):
        row = pd.Series({"baseline_mean_revenue": 100.0, "revenue": 100.0})

        result = data_wranglers._baseline_flag(row)

        assert result == "neutral"


class TestSharpFlag:
    def test_returns_na_when_prior_day_is_zero(self):
        row = pd.Series({"prior_day_revenue": 0.0, "revenue": 100.0})

        result = data_wranglers._sharp_flag(row)

        assert result == "na"

    def test_returns_sharp_rise_when_revenue_spikes(self):
        row = pd.Series({"prior_day_revenue": 100.0, "revenue": 140.0})

        result = data_wranglers._sharp_flag(row)

        assert result == "sharp_rise"

    def test_returns_sharp_drop_when_revenue_plummets(self):
        row = pd.Series({"prior_day_revenue": 100.0, "revenue": 60.0})

        result = data_wranglers._sharp_flag(row)

        assert result == "sharp_drop"

    def test_returns_none_string_otherwise(self):
        row = pd.Series({"prior_day_revenue": 100.0, "revenue": 100.0})

        result = data_wranglers._sharp_flag(row)

        assert result == "none"


class TestFinalStatus:
    def test_returns_blue_when_overperforming_and_sharp_rise(self):
        row = pd.Series(
            {"baseline_flag": "overperforming", "sharp_flag": "sharp_rise"})

        result = data_wranglers._final_status(row)

        assert result == "blue"

    def test_returns_green_when_overperforming_only(self):
        row = pd.Series(
            {"baseline_flag": "overperforming", "sharp_flag": "none"})

        result = data_wranglers._final_status(row)

        assert result == "green"

    def test_returns_red_when_underperformer_and_sharp_drop(self):
        row = pd.Series(
            {"baseline_flag": "underperformer", "sharp_flag": "sharp_drop"})

        result = data_wranglers._final_status(row)

        assert result == "red"

    def test_returns_orange_when_underperformer_only(self):
        row = pd.Series(
            {"baseline_flag": "underperformer", "sharp_flag": "none"})

        result = data_wranglers._final_status(row)

        assert result == "orange"

    def test_returns_grey_otherwise(self):
        row = pd.Series({"baseline_flag": "neutral", "sharp_flag": "none"})

        result = data_wranglers._final_status(row)

        assert result == "grey"


class TestStatusReason:
    def test_returns_missing_report_reason(self):
        row = pd.Series({"missing_report": True,
                         "status_colour": "grey", "low_activity": False})

        result = data_wranglers._status_reason(row)

        assert result == "No transactions reported yesterday."

    def test_returns_red_reason(self):
        row = pd.Series({"missing_report": False,
                         "status_colour": "red", "low_activity": False})

        result = data_wranglers._status_reason(row)

        assert result == "Revenue is below baseline and sharply down vs prior day."

    def test_returns_low_activity_reason(self):
        row = pd.Series({"missing_report": False,
                         "status_colour": "grey", "low_activity": True})

        result = data_wranglers._status_reason(row)

        assert result == "Sales count is unusually low vs the 7-day baseline."

    def test_returns_default_reason(self):
        row = pd.Series({"missing_report": False,
                         "status_colour": "grey", "low_activity": False})

        result = data_wranglers._status_reason(row)

        assert result == "No unusual signals detected."


class TestBuildMergedTruckData:
    def test_merges_expected_and_actual_trucks_filling_missing_with_zero(self):
        expected_trucks_df = pd.DataFrame(
            {"truck_id": [1, 2], "truck_name": ["Alpha", "Beta"]})
        truck_day_df = pd.DataFrame({"truck_id": [1], "truck_name": [
                                    "Alpha"], "revenue": [200.0], "sales_count": [10], "avg_sale_value": [20.0]})
        fleet_metrics = {"fleet_revenue": 200.0, "fleet_sales": 10}

        result = data_wranglers.build_merged_truck_data(
            expected_trucks_df, truck_day_df, fleet_metrics)

        beta_row = result[result["truck_name"] == "Beta"].iloc[0]
        assert beta_row["revenue"] == 0.0
        assert beta_row["sales_count"] == 0

    def test_calculates_contribution_pct_relative_to_fleet_revenue(self):
        expected_trucks_df = pd.DataFrame(
            {"truck_id": [1], "truck_name": ["Alpha"]})
        truck_day_df = pd.DataFrame({"truck_id": [1], "truck_name": [
                                    "Alpha"], "revenue": [200.0], "sales_count": [10], "avg_sale_value": [20.0]})
        fleet_metrics = {"fleet_revenue": 200.0, "fleet_sales": 10}

        result = data_wranglers.build_merged_truck_data(
            expected_trucks_df, truck_day_df, fleet_metrics)

        assert result.iloc[0]["contribution_pct"] == 100.0

    def test_contribution_pct_is_zero_when_fleet_revenue_is_zero(self):
        expected_trucks_df = pd.DataFrame(
            {"truck_id": [1], "truck_name": ["Alpha"]})
        truck_day_df = pd.DataFrame({"truck_id": [1], "truck_name": [
                                    "Alpha"], "revenue": [0.0], "sales_count": [0], "avg_sale_value": [0.0]})
        fleet_metrics = {"fleet_revenue": 0.0, "fleet_sales": 0}

        result = data_wranglers.build_merged_truck_data(
            expected_trucks_df, truck_day_df, fleet_metrics)

        assert result.iloc[0]["contribution_pct"] == 0.0


class TestBuildTrendFrame:
    def test_appends_report_day_metrics_to_historical_data(self):
        daily_df = pd.DataFrame({"truck_id": [1], "truck_name": ["Alpha"], "tx_date": [
                                 pd.Timestamp("2026-07-01")], "revenue": [100.0], "sales_count": [5]})
        truck_day_df = pd.DataFrame({"truck_id": [1], "truck_name": [
                                    "Alpha"], "revenue": [150.0], "sales_count": [7], "avg_sale_value": [21.43]})
        report_date = date(2026, 7, 2)

        result = data_wranglers.build_trend_frame(
            daily_df, truck_day_df, report_date)

        assert len(result) == 2
        report_day_row = result[result["tx_date"]
                                == pd.Timestamp(report_date)].iloc[0]
        assert report_day_row["revenue"] == 150.0


class TestBuildCompleteDailyFrame:
    def test_zero_fills_missing_truck_days(self):
        daily_df = pd.DataFrame({"truck_id": [1], "tx_date": [
                                 pd.Timestamp("2026-07-01")], "revenue": [50.0], "sales_count": [2]})
        expected_trucks_df = pd.DataFrame(
            {"truck_id": [1, 2], "truck_name": ["Alpha", "Beta"]})
        baseline_start = date(2026, 7, 1)
        report_date = date(2026, 7, 2)

        result = data_wranglers.build_complete_daily_frame(
            daily_df, expected_trucks_df, baseline_start, report_date)

        assert len(result) == 4
        beta_row = result[(result["truck_name"] == "Beta") & (
            result["tx_date"] == pd.Timestamp("2026-07-01"))].iloc[0]
        assert beta_row["revenue"] == 0.0
        assert beta_row["sales_count"] == 0


class TestCalculateBaselineStats:
    def test_calculates_mean_revenue_and_sales_within_range(self):
        daily_df = pd.DataFrame({
            "truck_id": [1, 1, 1],
            "tx_date": pd.to_datetime(["2026-06-01", "2026-06-02", "2026-06-03"]),
            "revenue": [100.0, 200.0, 300.0],
            "sales_count": [5, 10, 15],
        })

        result = data_wranglers.calculate_baseline_stats(
            daily_df, date(2026, 6, 1), date(2026, 6, 2))

        assert result.iloc[0]["baseline_mean_revenue"] == 150.0
        assert result.iloc[0]["baseline_mean_sales"] == 7.5


class TestCalculatePriorDayStats:
    def test_returns_revenue_for_matching_prior_day(self):
        daily_df = pd.DataFrame({
            "truck_id": [1, 1],
            "tx_date": pd.to_datetime(["2026-07-01", "2026-07-02"]),
            "revenue": [80.0, 999.0],
        })

        result = data_wranglers.calculate_prior_day_stats(
            daily_df, date(2026, 7, 1))

        assert len(result) == 1
        assert result.iloc[0]["prior_day_revenue"] == 80.0


class TestMergeBaselineAndPriorStats:
    def test_fills_missing_baseline_and_prior_values_with_zero(self):
        merged = pd.DataFrame({"truck_id": [1, 2]})
        baseline_stats = pd.DataFrame(
            {"truck_id": [1], "baseline_mean_revenue": [100.0], "baseline_mean_sales": [5.0]})
        prior_day_stats = pd.DataFrame(
            {"truck_id": [1], "prior_day_revenue": [90.0]})

        result = data_wranglers.merge_baseline_and_prior_stats(
            merged, baseline_stats, prior_day_stats)

        missing_truck_row = result[result["truck_id"] == 2].iloc[0]
        assert missing_truck_row["baseline_mean_revenue"] == 0.0
        assert missing_truck_row["baseline_mean_sales"] == 0.0
        assert missing_truck_row["prior_day_revenue"] == 0.0


class TestApplyStatusFlags:
    def test_adds_baseline_sharp_and_status_colour_columns(self):
        merged = pd.DataFrame({
            "revenue": [140.0],
            "baseline_mean_revenue": [100.0],
            "prior_day_revenue": [100.0],
        })

        result = data_wranglers.apply_status_flags(merged)

        assert result.iloc[0]["baseline_flag"] == "overperforming"
        assert result.iloc[0]["sharp_flag"] == "sharp_rise"
        assert result.iloc[0]["status_colour"] == "blue"


class TestAddActivityIndicators:
    def test_flags_low_activity_when_sales_below_baseline_threshold(self):
        merged = pd.DataFrame(
            {"baseline_mean_sales": [10.0], "sales_count": [5]})

        result = data_wranglers.add_activity_indicators(merged)

        assert bool(result.iloc[0]["low_activity"]) is True

    def test_flags_missing_report_when_sales_count_is_zero(self):
        merged = pd.DataFrame(
            {"baseline_mean_sales": [10.0], "sales_count": [0]})

        result = data_wranglers.add_activity_indicators(merged)

        assert bool(result.iloc[0]["missing_report"]) is True


class TestCalculateTruckDeltas:
    def test_calculates_baseline_and_day_delta_pct(self):
        merged = pd.DataFrame({
            "revenue": [150.0],
            "baseline_mean_revenue": [100.0],
            "prior_day_revenue": [100.0],
        })

        result = data_wranglers.calculate_truck_deltas(merged)

        assert result.iloc[0]["baseline_delta_pct"] == 50.0
        assert result.iloc[0]["day_delta_pct"] == 50.0


class TestApplyStatusReason:
    def test_adds_reason_column_based_on_status(self):
        merged = pd.DataFrame({
            "missing_report": [True],
            "status_colour": ["grey"],
            "low_activity": [False],
        })

        result = data_wranglers.apply_status_reason(merged)

        assert result.iloc[0]["reason"] == "No transactions reported yesterday."


class TestCalculateFleetDayChange:
    def test_calculates_percent_change_vs_prior_day(self):
        daily_complete = pd.DataFrame({
            "tx_date": pd.to_datetime(["2026-07-01", "2026-07-01"]),
            "revenue": [100.0, 50.0],
        })

        result = data_wranglers.calculate_fleet_day_change(
            daily_complete, date(2026, 7, 1), 225.0)

        assert result == 50.0

    def test_returns_none_when_prior_day_revenue_is_zero(self):
        daily_complete = pd.DataFrame({
            "tx_date": pd.to_datetime(["2026-07-01"]),
            "revenue": [0.0],
        })

        result = data_wranglers.calculate_fleet_day_change(
            daily_complete, date(2026, 7, 1), 100.0)

        assert result is None


class TestFilterActiveTrucks:
    def test_excludes_rows_with_zero_sales_count(self):
        trend_daily_df = pd.DataFrame({"sales_count": [0, 5, 0, 3]})

        result = data_wranglers.filter_active_trucks(trend_daily_df)

        assert len(result) == 2


class TestFindLowestPerformersPerDay:
    def test_identifies_lowest_revenue_truck_per_day(self):
        ranking_df = pd.DataFrame({
            "tx_date": pd.to_datetime(["2026-07-01", "2026-07-01", "2026-07-02"]),
            "truck_id": [1, 2, 1],
            "revenue": [100.0, 50.0, 80.0],
        })

        result = data_wranglers.find_lowest_performers_per_day(ranking_df)

        assert len(result) == 2
        assert set(result["truck_id"]) == {2, 1}

    def test_includes_tied_lowest_performers(self):
        ranking_df = pd.DataFrame({
            "tx_date": pd.to_datetime(["2026-07-01", "2026-07-01"]),
            "truck_id": [1, 2],
            "revenue": [50.0, 50.0],
        })

        result = data_wranglers.find_lowest_performers_per_day(ranking_df)

        assert len(result) == 2


class TestCalculateLowestPerformerCounts:
    def test_flags_recurring_lowest_when_three_or_more_days(self):
        lowest_rows = pd.DataFrame({
            "truck_id": [1, 1, 1, 2],
            "truck_name": ["A", "A", "A", "B"],
            "tx_date": pd.to_datetime(["2026-07-01", "2026-07-02", "2026-07-03", "2026-07-01"]),
        })

        result = data_wranglers.calculate_lowest_performer_counts(
            lowest_rows)

        truck_a = result[result["truck_id"] == 1].iloc[0]
        truck_b = result[result["truck_id"] == 2].iloc[0]
        assert truck_a["lowest_days_count"] == 3
        assert bool(truck_a["is_recurring_lowest"]) is True
        assert bool(truck_b["is_recurring_lowest"]) is False


class TestMergeLowestPatterns:
    def test_fills_missing_trucks_with_zero_count_and_false_flag(self):
        merged = pd.DataFrame({"truck_id": [1, 2]})
        lowest_counts = pd.DataFrame({
            "truck_id": [1],
            "truck_name": ["A"],
            "lowest_days_count": [3],
            "is_recurring_lowest": [True],
        })

        result = data_wranglers.merge_lowest_patterns(merged, lowest_counts)

        missing_truck_row = result[result["truck_id"] == 2].iloc[0]
        assert missing_truck_row["lowest_days_count"] == 0
        assert bool(missing_truck_row["is_recurring_lowest"]) is False
