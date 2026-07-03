"""Athena data wranglers for the daily HTML report.

This module handles all data loading and transformation operations.
Data is loaded from Athena and pre-processed into formats ready for display.
"""

from datetime import date, timedelta

import awswrangler as wr
import pandas as pd


def load_previous_day_fleet_metrics(
        db_name: str,
        s3_output: str,
        report_date: date,
) -> dict[str, float]:
    """Load fleet revenue and sales count for the report date."""
    report_date_literal = f"DATE '{report_date.isoformat()}'"
    query = f"""
	SELECT 
        COALESCE(SUM(total), 0) / 100.0 AS total_revenue,
        COUNT(*) AS fleet_sales
    FROM FACT_Transaction
	WHERE year = YEAR({report_date_literal})
	  AND month = MONTH({report_date_literal})
	  AND day = DAY({report_date_literal})
	"""

    df = wr.athena.read_sql_query(
        sql=query,
        database=db_name,
        s3_output=s3_output,
    )

    if df.empty:
        return {"fleet_revenue": 0.0, "fleet_sales": 0}

    return {
        "fleet_revenue": float(df.iloc[0]["total_revenue"] or 0.0),
        "fleet_sales": int(df.iloc[0]["fleet_sales"] or 0),
    }


def load_previous_day_truck_metrics(
        db_name: str,
        s3_output: str,
        report_date: date,
) -> pd.DataFrame:
    """Load per-truck revenue, sales count, and average sale value for the report date."""
    report_date_literal = f"DATE '{report_date.isoformat()}'"
    query = f"""
	SELECT
		d.truck_id,
		d.truck_name,
        COALESCE(SUM(f.total), 0) / 100.0 AS revenue,
		COUNT(*) AS sales_count,
        ROUND(COALESCE(AVG(f.total), 0) / 100.0, 2) AS avg_sale_value
	FROM FACT_Transaction f
	JOIN DIM_Truck d ON f.truck_id = d.truck_id
    WHERE f.year = YEAR({report_date_literal})
      AND f.month = MONTH({report_date_literal})
      AND f.day = DAY({report_date_literal})
	GROUP BY d.truck_id, d.truck_name
	ORDER BY revenue DESC
	"""

    df = wr.athena.read_sql_query(
        sql=query,
        database=db_name,
        s3_output=s3_output,
    )
    return df


def load_daily_truck_metrics(
        db_name: str,
        s3_output: str,
        report_date: date,
) -> pd.DataFrame:
    """Load per-truck daily revenue and sales count for 30 baseline days before the report date."""

    report_date_literal = f"DATE '{report_date.isoformat()}'"
    query = f"""
	SELECT
		d.truck_id,
		d.truck_name,
		CAST(CONCAT(CAST(f.year AS VARCHAR), '-', LPAD(CAST(f.month AS VARCHAR), 2, '0'), '-', LPAD(CAST(f.day AS VARCHAR), 2, '0')) AS DATE) AS tx_date,
        COALESCE(SUM(f.total), 0) / 100.0 AS revenue,
		COUNT(*) AS sales_count
	FROM FACT_Transaction f
	JOIN DIM_Truck d ON f.truck_id = d.truck_id
    WHERE CAST(CONCAT(CAST(f.year AS VARCHAR), '-', LPAD(CAST(f.month AS VARCHAR), 2, '0'), '-', LPAD(CAST(f.day AS VARCHAR), 2, '0')) AS DATE) 
    BETWEEN DATE_ADD('day', -31, {report_date_literal}) AND DATE_ADD('day', -1, {report_date_literal})
	GROUP BY d.truck_id, d.truck_name, f.year, f.month, f.day
	ORDER BY d.truck_name, f.year, f.month, f.day
	"""

    df = wr.athena.read_sql_query(
        sql=query,
        database=db_name,
        s3_output=s3_output,
    )
    return df


def load_expected_active_trucks(
        db_name: str,
        s3_output: str,
) -> pd.DataFrame:
    """Load expected trucks from DIM_Truck."""
    query = """
	SELECT truck_id, truck_name
	FROM DIM_Truck
	ORDER BY truck_name
	"""

    return wr.athena.read_sql_query(
        sql=query,
        database=db_name,
        s3_output=s3_output,
    )


# Data Transformation Functions


def _safe_pct_change(current_value: float, reference_value: float) -> float | None:
    """Return percent change from reference to current, or None when undefined."""
    if reference_value == 0:
        return None
    return ((current_value - reference_value) / reference_value) * 100.0


def _baseline_flag(row: pd.Series) -> str:
    """Determine if truck is overperforming or underperforming baseline."""
    if row["baseline_mean_revenue"] == 0:
        return "na"
    if row["revenue"] >= row["baseline_mean_revenue"] * 1.40:
        return "overperforming"
    if row["revenue"] <= row["baseline_mean_revenue"] * 0.60:
        return "underperformer"
    return "neutral"


def _sharp_flag(row: pd.Series) -> str:
    """Determine if truck had sharp change vs prior day."""
    if row["prior_day_revenue"] == 0:
        return "na"
    if row["revenue"] >= row["prior_day_revenue"] * 1.40:
        return "sharp_rise"
    if row["revenue"] <= row["prior_day_revenue"] * 0.60:
        return "sharp_drop"
    return "none"


def _final_status(row: pd.Series) -> str:
    """Determine final status colour based on baseline and sharp flags."""
    if row["baseline_flag"] == "overperforming" and row["sharp_flag"] == "sharp_rise":
        return "blue"
    if row["baseline_flag"] == "overperforming":
        return "green"
    if row["baseline_flag"] == "underperformer" and row["sharp_flag"] == "sharp_drop":
        return "red"
    if row["baseline_flag"] == "underperformer":
        return "orange"
    return "grey"


def _status_reason(row: pd.Series) -> str:
    """Determine reason for truck status."""
    if row["missing_report"]:
        return "No transactions reported yesterday."
    if row["status_colour"] == "red":
        return "Revenue is below baseline and sharply down vs prior day."
    if row["status_colour"] == "orange":
        return "Revenue is materially below the 7-day baseline."
    if row["status_colour"] == "blue":
        return "Revenue is above baseline and sharply up vs prior day."
    if row["status_colour"] == "green":
        return "Revenue is materially above the 7-day baseline."
    if row["low_activity"]:
        return "Sales count is unusually low vs the 7-day baseline."
    return "No unusual signals detected."


def build_merged_truck_data(
        expected_trucks_df: pd.DataFrame,
        truck_day_df: pd.DataFrame,
        fleet_metrics: dict[str, float],
) -> pd.DataFrame:
    """Build core merged frame with expected trucks and their metrics."""
    expected_trucks_df = expected_trucks_df[[
        "truck_id", "truck_name"]].drop_duplicates()
    truck_day_df = truck_day_df[[
        "truck_id", "truck_name", "revenue", "sales_count", "avg_sale_value"]]

    merged = expected_trucks_df.merge(
        truck_day_df,
        on=["truck_id", "truck_name"],
        how="left",
    )

    for metric_col in ["revenue", "sales_count", "avg_sale_value"]:
        merged[metric_col] = merged[metric_col].fillna(0.0)

    merged["sales_count"] = merged["sales_count"].astype(int)
    merged["contribution_pct"] = (
        (merged["revenue"] / fleet_metrics["fleet_revenue"] * 100.0)
        if fleet_metrics["fleet_revenue"] > 0
        else 0.0
    )

    return merged


def build_trend_frame(
        daily_df: pd.DataFrame,
        truck_day_df: pd.DataFrame,
        report_date: date,
) -> pd.DataFrame:
    """Build trend frame by appending today's metrics to historical data."""
    report_day_trend_df = truck_day_df[[
        "truck_id", "truck_name", "revenue", "sales_count"]].copy()
    report_day_trend_df["tx_date"] = pd.to_datetime(report_date)

    trend_daily_df = pd.concat(
        [
            daily_df[["truck_id", "truck_name",
                      "tx_date", "revenue", "sales_count"]],
            report_day_trend_df,
        ],
        ignore_index=True,
    )
    return trend_daily_df


def build_complete_daily_frame(
        daily_df: pd.DataFrame,
        expected_trucks_df: pd.DataFrame,
        baseline_start: date,
        report_date: date,
) -> pd.DataFrame:
    """Build complete daily frame with all trucks and all dates (zero-filled)."""
    all_dates = pd.date_range(start=baseline_start, end=report_date, freq="D")
    expected_grid = pd.MultiIndex.from_product(
        [expected_trucks_df["truck_id"].tolist(), all_dates],
        names=["truck_id", "tx_date"],
    ).to_frame(index=False)
    names = expected_trucks_df.set_index("truck_id")["truck_name"]
    expected_grid["truck_name"] = expected_grid["truck_id"].map(names)

    daily_complete = expected_grid.merge(
        daily_df[["truck_id", "tx_date", "revenue", "sales_count"]],
        on=["truck_id", "tx_date"],
        how="left",
    )
    daily_complete["revenue"] = daily_complete["revenue"].fillna(0.0)
    daily_complete["sales_count"] = daily_complete["sales_count"].fillna(
        0).astype(int)

    return daily_complete


def calculate_baseline_stats(
        daily_df: pd.DataFrame,
        baseline_start: date,
        baseline_end: date,
) -> pd.DataFrame:
    """Calculate mean revenue and sales for baseline period."""
    baseline_mask = (daily_df["tx_date"].dt.date >= baseline_start) & (
        daily_df["tx_date"].dt.date <= baseline_end
    )
    return (
        daily_df.loc[baseline_mask]
        .groupby("truck_id", as_index=False)
        .agg(
            baseline_mean_revenue=("revenue", "mean"),
            baseline_mean_sales=("sales_count", "mean"),
        )
    )


def calculate_prior_day_stats(
        daily_df: pd.DataFrame,
        prior_day: date,
) -> pd.DataFrame:
    """Calculate revenue for prior day."""
    return daily_df[daily_df["tx_date"].dt.date == prior_day][
        ["truck_id", "revenue"]
    ].rename(columns={"revenue": "prior_day_revenue"})


def merge_baseline_and_prior_stats(
        merged: pd.DataFrame,
        baseline_stats: pd.DataFrame,
        prior_day_stats: pd.DataFrame,
) -> pd.DataFrame:
    """Merge baseline and prior day stats into main frame, filling missing values."""
    merged = merged.merge(baseline_stats, on="truck_id", how="left")
    merged = merged.merge(prior_day_stats, on="truck_id", how="left")
    merged["baseline_mean_revenue"] = merged["baseline_mean_revenue"].fillna(
        0.0)
    merged["baseline_mean_sales"] = merged["baseline_mean_sales"].fillna(0.0)
    merged["prior_day_revenue"] = merged["prior_day_revenue"].fillna(0.0)
    return merged


def apply_status_flags(merged: pd.DataFrame) -> pd.DataFrame:
    """Apply baseline, sharp, and final status flags."""
    merged["baseline_flag"] = merged.apply(_baseline_flag, axis=1)
    merged["sharp_flag"] = merged.apply(_sharp_flag, axis=1)
    merged["status_colour"] = merged.apply(_final_status, axis=1)
    return merged


def add_activity_indicators(merged: pd.DataFrame) -> pd.DataFrame:
    """Add low_activity and missing_report flags."""
    merged["low_activity"] = (
        (merged["baseline_mean_sales"] > 0)
        & (merged["sales_count"] <= merged["baseline_mean_sales"] * 0.70)
    )
    merged["missing_report"] = merged["sales_count"] == 0
    return merged


def calculate_truck_deltas(merged: pd.DataFrame) -> pd.DataFrame:
    """Calculate percent change deltas for baseline and prior day."""
    merged["baseline_delta_pct"] = merged.apply(
        lambda row: _safe_pct_change(
            row["revenue"], row["baseline_mean_revenue"]),
        axis=1,
    )
    merged["day_delta_pct"] = merged.apply(
        lambda row: _safe_pct_change(row["revenue"], row["prior_day_revenue"]),
        axis=1,
    )
    return merged


def apply_status_reason(merged: pd.DataFrame) -> pd.DataFrame:
    """Add human-readable reason for status."""
    merged["reason"] = merged.apply(_status_reason, axis=1)
    return merged


def calculate_fleet_day_change(
        daily_complete: pd.DataFrame,
        prior_day: date,
        fleet_revenue: float,
) -> float | None:
    """Calculate fleet-level day-over-day percent change."""
    fleet_prior_revenue = float(
        daily_complete[daily_complete["tx_date"].dt.date ==
                       prior_day]["revenue"].sum()
    )
    return _safe_pct_change(fleet_revenue, fleet_prior_revenue)


def apply_baseline_and_status(
        merged: pd.DataFrame,
        daily_df: pd.DataFrame,
        daily_complete: pd.DataFrame,
        baseline_start: date,
        baseline_end: date,
        prior_day: date,
        fleet_revenue: float,
) -> tuple[pd.DataFrame, float | None]:
    """Apply baseline statistics, status flags, and day-over-day calculations."""
    baseline_stats = calculate_baseline_stats(
        daily_df, baseline_start, baseline_end)
    prior_day_stats = calculate_prior_day_stats(daily_df, prior_day)

    merged = merge_baseline_and_prior_stats(
        merged, baseline_stats, prior_day_stats)
    merged = apply_status_flags(merged)
    merged = add_activity_indicators(merged)
    merged = calculate_truck_deltas(merged)
    merged = apply_status_reason(merged)

    fleet_day_change_pct = calculate_fleet_day_change(
        daily_complete, prior_day, fleet_revenue)

    return merged, fleet_day_change_pct


def filter_active_trucks(trend_daily_df: pd.DataFrame) -> pd.DataFrame:
    """Filter to only trucks with sales (exclude zero-activity days)."""
    return trend_daily_df[trend_daily_df["sales_count"] > 0].copy()


def find_lowest_performers_per_day(ranking_df: pd.DataFrame) -> pd.DataFrame:
    """Identify the lowest revenue truck for each day."""
    daily_min = ranking_df.groupby("tx_date", as_index=False).agg(
        min_revenue=("revenue", "min"))
    lowest_rows = ranking_df.merge(daily_min, on="tx_date", how="left")
    return lowest_rows[lowest_rows["revenue"] == lowest_rows["min_revenue"]]


def calculate_lowest_performer_counts(lowest_rows: pd.DataFrame) -> pd.DataFrame:
    """Count how many distinct days each truck was the lowest performer."""
    lowest_counts = (
        lowest_rows.groupby(["truck_id", "truck_name"], as_index=False)
        .agg(lowest_days_count=("tx_date", "nunique"))
    )
    lowest_counts["is_recurring_lowest"] = lowest_counts["lowest_days_count"] >= 3
    return lowest_counts


def merge_lowest_patterns(
        merged: pd.DataFrame,
        lowest_counts: pd.DataFrame,
) -> pd.DataFrame:
    """Merge lowest performer flags into main frame."""
    merged = merged.merge(
        lowest_counts[["truck_id", "lowest_days_count",
                       "is_recurring_lowest"]],
        on="truck_id",
        how="left",
    )
    merged["lowest_days_count"] = merged["lowest_days_count"].fillna(
        0).astype(int)
    merged["is_recurring_lowest"] = merged["is_recurring_lowest"].fillna(False)
    return merged


def compute_lowest_patterns(
        merged: pd.DataFrame,
        trend_daily_df: pd.DataFrame,
        trailing_start: date,
        report_date: date,
) -> tuple[pd.DataFrame, pd.DataFrame, int]:
    """Compute recurring lowest-performer counts and daily lowest rows."""
    trailing_mask = (trend_daily_df["tx_date"].dt.date >= trailing_start) & (
        trend_daily_df["tx_date"].dt.date <= report_date
    )
    trailing_df = trend_daily_df.loc[trailing_mask].copy()

    ranking_df = filter_active_trucks(trailing_df)
    lowest_rows = find_lowest_performers_per_day(ranking_df)
    lowest_counts = calculate_lowest_performer_counts(lowest_rows)

    merged = merge_lowest_patterns(merged, lowest_counts)

    days_with_tracked_data = ranking_df["tx_date"].dt.date.nunique()
    return merged, lowest_rows, days_with_tracked_data


def prepare_report_data(
        glue_db_name: str,
        s3_output: str,
        report_date: date,
) -> dict:
    """Load and prepare all data needed for report generation."""
    baseline_start = report_date - timedelta(days=30)
    baseline_end = report_date - timedelta(days=1)
    trailing_start = report_date - timedelta(days=29)
    prior_day = report_date - timedelta(days=1)

    # Load raw data
    fleet_metrics = load_previous_day_fleet_metrics(
        glue_db_name, s3_output, report_date)
    truck_day_df = load_previous_day_truck_metrics(
        glue_db_name, s3_output, report_date)
    expected_trucks_df = load_expected_active_trucks(glue_db_name, s3_output)
    daily_df = load_daily_truck_metrics(glue_db_name, s3_output, report_date)
    daily_df["tx_date"] = pd.to_datetime(daily_df["tx_date"])

    # Build merged frame
    merged = build_merged_truck_data(
        expected_trucks_df, truck_day_df, fleet_metrics)

    # Build trend frames
    trend_daily_df = build_trend_frame(daily_df, truck_day_df, report_date)
    daily_complete = build_complete_daily_frame(
        daily_df, expected_trucks_df, baseline_start, report_date
    )

    # Apply baseline and status calculations
    merged, fleet_day_change_pct = apply_baseline_and_status(
        merged,
        daily_df,
        daily_complete,
        baseline_start,
        baseline_end,
        prior_day,
        fleet_metrics["fleet_revenue"],
    )

    # Compute lowest patterns
    merged, lowest_rows, days_with_tracked_data = compute_lowest_patterns(
        merged,
        trend_daily_df,
        trailing_start,
        report_date,
    )

    return {
        "fleet_metrics": fleet_metrics,
        "fleet_day_change_pct": fleet_day_change_pct,
        "merged": merged,
        "lowest_rows": lowest_rows,
        "days_with_tracked_data": days_with_tracked_data,
    }
