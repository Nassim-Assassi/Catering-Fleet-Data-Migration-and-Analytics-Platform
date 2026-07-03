"""Generate a daily HTML performance report for the food truck fleet.

This module handles all display logic and HTML rendering.
Data preparation is handled by the report_data_wranglers module.
"""

from datetime import date, datetime, timedelta
from html import escape
from os import environ

import boto3
import pandas as pd
from dotenv import load_dotenv

from report_data_wranglers import prepare_report_data


STATUS_COLOURS = {
    "blue": "#2563eb",
    "green": "#16a34a",
    "grey": "#6b7280",
    "orange": "#ea580c",
    "red": "#dc2626",
}


# Display & Formatting Functions


def _status_label(status: str) -> str:
    """Map status colour to human-readable label."""
    labels = {
        "blue": "Overperforming + sharp rise",
        "green": "Overperforming",
        "grey": "Neutral",
        "orange": "Underperformer",
        "red": "Underperformer + sharp drop",
    }
    return labels.get(status, "Neutral")


def _status_chip(row: pd.Series) -> str:
    """Generate HTML span with status badge."""
    colour = STATUS_COLOURS.get(row["status_colour"], STATUS_COLOURS["grey"])
    label = _status_label(row["status_colour"])
    return f'<span class="chip" style="background:{colour};">{escape(label)}</span>'


def _format_money(value: float) -> str:
    """Format value as GBP currency."""
    return f"GBP {value:,.2f}"


def _format_pct(value: float | None) -> str:
    """Format value as percentage, or N/A if None."""
    if value is None:
        return "N/A"
    return f"{value:+.1f}%"


def _render_table(df: pd.DataFrame, columns: list[tuple[str, str]]) -> str:
    """Render DataFrame as HTML table with specified columns."""
    headers = "".join(f"<th>{escape(title)}</th>" for title, _ in columns)
    rows: list[str] = []
    for _, row in df.iterrows():
        row_cells = "".join(
            f"<td>{escape(str(row[col]))}</td>" for _, col in columns
        )
        rows.append(f"<tr>{row_cells}</tr>")
    if not rows:
        rows.append('<tr><td colspan="100">No data available.</td></tr>')
    return f"<table><thead><tr>{headers}</tr></thead><tbody>{''.join(rows)}</tbody></table>"


def _build_top5_display(merged: pd.DataFrame) -> pd.DataFrame:
    """Build top 5 trucks by revenue display."""
    ranked = merged.sort_values(
        "revenue", ascending=False).reset_index(drop=True)
    top5 = ranked.head(5).copy()
    return top5.assign(
        Revenue=top5["revenue"].map(_format_money),
        Sales=top5["sales_count"],
        RevenueSharePct=top5["contribution_pct"].map(lambda x: f"{x:.1f}%"),
    )[["truck_name", "Revenue", "Sales", "RevenueSharePct"]].rename(
        columns={"truck_name": "Truck"}
    )


def _build_bottom5_display(merged: pd.DataFrame) -> pd.DataFrame:
    """Build bottom 5 trucks by revenue display."""
    ranked = merged.sort_values(
        "revenue", ascending=False).reset_index(drop=True)
    bottom5 = ranked.tail(5).sort_values("revenue", ascending=True).copy()
    return bottom5.assign(
        Revenue=bottom5["revenue"].map(_format_money),
        Sales=bottom5["sales_count"],
        RevenueSharePct=bottom5["contribution_pct"].map(lambda x: f"{x:.1f}%"),
    )[["truck_name", "Revenue", "Sales", "RevenueSharePct"]].rename(
        columns={"truck_name": "Truck"}
    )


def _build_details_display(merged: pd.DataFrame) -> pd.DataFrame:
    """Build full ranked details display."""
    ranked = merged.sort_values(
        "revenue", ascending=False).reset_index(drop=True)
    return ranked.assign(
        Revenue=ranked["revenue"].map(_format_money),
        Sales=ranked["sales_count"],
        AvgSale=ranked["avg_sale_value"].map(_format_money),
        RevenueSharePct=ranked["contribution_pct"].map(lambda x: f"{x:.1f}%"),
    )[["truck_name", "Revenue", "Sales", "AvgSale", "RevenueSharePct"]].rename(
        columns={"truck_name": "Truck"}
    )


def _build_status_display(merged: pd.DataFrame) -> pd.DataFrame:
    """Build status and reason display."""
    ranked = merged.sort_values(
        "revenue", ascending=False).reset_index(drop=True)
    return ranked.assign(
        Truck=ranked["truck_name"],
        Status=ranked["status_colour"].map(_status_label),
        BaselineDelta=ranked["baseline_delta_pct"].map(_format_pct),
        DayDelta=ranked["day_delta_pct"].map(_format_pct),
        MissingReport=ranked["missing_report"].map(
            lambda x: "Yes" if x else "No"),
        LowActivity=ranked["low_activity"].map(lambda x: "Yes" if x else "No"),
        Reason=ranked["reason"],
    )[["Truck", "Status", "BaselineDelta", "DayDelta", "MissingReport", "LowActivity", "Reason"]]


def _build_flagged_rows(merged: pd.DataFrame) -> list[str]:
    """Build flagged trucks HTML table rows."""
    flagged = merged[
        (merged["missing_report"])
        | (merged["low_activity"])
        | (merged["status_colour"].isin(["blue", "orange", "red"]))
        | (merged["is_recurring_lowest"])
    ].copy()
    flagged["priority"] = flagged["status_colour"].map(
        {"red": 1, "orange": 2, "blue": 3}
    ).fillna(4)
    flagged = flagged.sort_values(
        ["priority", "revenue"], ascending=[True, False]
    ).drop(columns=["priority"])

    rows: list[str] = []
    for _, row in flagged.iterrows():
        rows.append(
            "<tr>"
            f"<td>{escape(str(row['truck_name']))}</td>"
            f"<td>{_status_chip(row)}</td>"
            f"<td>{escape(_format_money(float(row['revenue'])))}</td>"
            f"<td>{escape(_format_pct(row['day_delta_pct']))}</td>"
            f"<td>{'Yes' if row['missing_report'] else 'No'}</td>"
            f"<td>{'Yes' if row['is_recurring_lowest'] else 'No'}</td>"
            f"<td>{escape(str(row['reason']))}</td>"
            "</tr>"
        )
    if not rows:
        rows.append(
            '<tr><td colspan="7">No flagged trucks for the day.</td></tr>')
    return rows


def _build_recurring_lowest_display(merged: pd.DataFrame) -> pd.DataFrame:
    """Build recurring lowest performers display."""
    recurring_lowest = merged[merged["is_recurring_lowest"]].sort_values(
        ["lowest_days_count", "revenue"], ascending=[False, True]
    )
    return recurring_lowest.assign(
        Truck=recurring_lowest["truck_name"],
        LowestDays=recurring_lowest["lowest_days_count"],
        ReportDayRevenue=recurring_lowest["revenue"].map(_format_money),
    )[["Truck", "LowestDays", "ReportDayRevenue"]]


def _build_daily_lowest_display(lowest_rows: pd.DataFrame) -> pd.DataFrame:
    """Build daily lowest performers by date display."""
    if lowest_rows.empty:
        return pd.DataFrame(
            columns=["Date", "Lowest Truck(s)",
                     "Lowest Revenue", "Tied Trucks"]
        )

    daily_lowest_summary = (
        lowest_rows.groupby("tx_date", as_index=False)
        .agg(
            lowest_revenue=("revenue", "min"),
            lowest_trucks=(
                "truck_name", lambda names: ", ".join(sorted(set(names)))),
            tied_trucks=("truck_id", "nunique"),
        )
        .sort_values("tx_date")
    )

    return pd.DataFrame(
        {
            "Date": daily_lowest_summary["tx_date"].dt.strftime("%Y-%m-%d"),
            "Lowest Truck(s)": daily_lowest_summary["lowest_trucks"],
            "Lowest Revenue": daily_lowest_summary["lowest_revenue"].map(_format_money),
            "Tied Trucks": daily_lowest_summary["tied_trucks"],
        }
    )


def generate_daily_report_data(
    glue_db_name: str,
    s3_output: str,
    report_date: date | None = None,
) -> dict:
    """Collect and prepare raw data for the daily report.

    This function handles all data collection and transformation from source data.

    Args:
        glue_db_name: AWS Glue database name
        s3_output: S3 path for Athena query results
        report_date: Date for report (defaults to yesterday)

    Returns:
        Dictionary containing raw prepared data:
        - merged: Merged truck performance data
        - lowest_rows: Lowest performing trucks data
        - fleet_metrics: Fleet-level metrics
        - fleet_day_change_pct: Day-over-day percentage change
        - days_with_tracked_data: Count of days with data
        - report_date: The report date used
    """
    report_date = report_date or (date.today() - timedelta(days=1))
    report_data = prepare_report_data(glue_db_name, s3_output, report_date)

    return {
        "merged": report_data["merged"],
        "lowest_rows": report_data["lowest_rows"],
        "fleet_metrics": report_data["fleet_metrics"],
        "fleet_day_change_pct": report_data["fleet_day_change_pct"],
        "days_with_tracked_data": report_data["days_with_tracked_data"],
        "report_date": report_date,
    }


def generate_daily_report(
    glue_db_name: str,
    s3_output: str,
    report_date: date | None = None,
) -> str:
    """Generate and return the daily HTML report content."""
    # Prepare raw data
    data = generate_daily_report_data(glue_db_name, s3_output, report_date)

    merged = data["merged"]
    lowest_rows = data["lowest_rows"]
    fleet_metrics = data["fleet_metrics"]
    fleet_day_change_pct = data["fleet_day_change_pct"]
    days_with_tracked_data = data["days_with_tracked_data"]
    report_date = data["report_date"]

    # Generate display components separately
    top5_display = _build_top5_display(merged)
    bottom5_display = _build_bottom5_display(merged)
    details_display = _build_details_display(merged)
    status_display = _build_status_display(merged)
    flagged_rows = _build_flagged_rows(merged)
    recurring_rows = _build_recurring_lowest_display(merged)
    daily_lowest_display = _build_daily_lowest_display(lowest_rows)

    # Render HTML
    html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Fleet Daily Report - {report_date.isoformat()}</title>
  <style>
	:root {{
	  --bg: #f8fafc;
	  --card: #ffffff;
	  --text: #0f172a;
	  --muted: #475569;
	  --line: #e2e8f0;
	  --accent: #0ea5a5;
	}}
	* {{ box-sizing: border-box; }}
	body {{ margin: 0; font-family: "Avenir Next", "Segoe UI", sans-serif; background: linear-gradient(180deg, #ecfeff 0%, var(--bg) 220px); color: var(--text); }}
	.container {{ max-width: 1180px; margin: 0 auto; padding: 24px; }}
	.header {{ margin-bottom: 16px; }}
	.header h1 {{ margin: 0; font-size: 1.8rem; }}
	.header p {{ margin: 6px 0 0; color: var(--muted); }}
	.cards {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 12px; margin: 18px 0; }}
	.card {{ background: var(--card); border: 1px solid var(--line); border-radius: 12px; padding: 16px; box-shadow: 0 1px 2px rgba(15, 23, 42, 0.06); }}
	.card h3 {{ margin: 0; font-size: 0.9rem; color: var(--muted); font-weight: 600; }}
	.card .metric {{ margin-top: 8px; font-size: 1.5rem; font-weight: 700; }}
	.section {{ background: var(--card); border: 1px solid var(--line); border-radius: 12px; padding: 16px; margin-bottom: 14px; }}
	.section h2 {{ margin: 0 0 10px; font-size: 1.1rem; }}
	.split {{ display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }}
	table {{ width: 100%; border-collapse: collapse; margin-top: 6px; }}
	th, td {{ text-align: left; padding: 9px 8px; border-bottom: 1px solid var(--line); vertical-align: top; }}
	th {{ color: var(--muted); font-size: 0.78rem; text-transform: uppercase; letter-spacing: 0.03em; }}
	.chip {{ color: #fff; font-size: 0.72rem; font-weight: 600; padding: 4px 8px; border-radius: 999px; display: inline-block; }}
	.collapsible-header {{ display: flex; align-items: center; cursor: pointer; user-select: none; }}
	.collapsible-header:hover {{ color: var(--accent); }}
	.collapsible-toggle {{ display: inline-block; margin-right: 8px; font-weight: bold; width: 20px; transition: transform 0.2s; }}
	.collapsible-toggle.collapsed {{ transform: rotate(-90deg); }}
	.collapsible-content {{ display: none; margin-top: 12px; }}
	.collapsible-content.expanded {{ display: block; }}
	@media (max-width: 900px) {{ .split {{ grid-template-columns: 1fr; }} }}
  </style>
  <script>
	function toggleCollapsible(event) {{
	  event.preventDefault();
	  const header = event.currentTarget;
	  const toggle = header.querySelector('.collapsible-toggle');
	  const content = header.nextElementSibling;
	  toggle.classList.toggle('collapsed');
	  content.classList.toggle('expanded');
	}}
	document.addEventListener('DOMContentLoaded', function() {{
	  document.querySelectorAll('.collapsible-header').forEach(header => {{
		header.addEventListener('click', toggleCollapsible);
	  }});
	}});
  </script>
</head>
<body>
  <div class="container">
	<div class="header">
	  <h1>Fleet Daily Report</h1>
	  <p>Report date: {report_date.isoformat()} | Generated at: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
	</div>

	<div class="cards">
	  <div class="card"><h3>Total Fleet Revenue</h3><div class="metric">{_format_money(float(fleet_metrics['fleet_revenue']))}</div></div>
	  <div class="card"><h3>Total Sales</h3><div class="metric">{int(fleet_metrics['fleet_sales'])}</div></div>
	  <div class="card"><h3>Day-over-Day Revenue Change</h3><div class="metric">{_format_pct(fleet_day_change_pct)}</div></div>
	</div>

	<div class="section">
	  <h2>Executive Summary</h2>
	  <div class="split">
		<div>
		  <h3>Top 5 Trucks</h3>
          {_render_table(top5_display, [("Truck", "Truck"), ("Revenue", "Revenue"), ("Sales", "Sales"), ("Revenue Share (%)", "RevenueSharePct")])}
		</div>
		<div>
		  <h3>Bottom 5 Trucks</h3>
          {_render_table(bottom5_display, [("Truck", "Truck"), ("Revenue", "Revenue"), ("Sales", "Sales"), ("Revenue Share (%)", "RevenueSharePct")])}
		</div>
	  </div>
	</div>

	<div class="section">
	  <h2>Flagged Trucks</h2>
	  <table>
		<thead>
		  <tr>
			<th>Truck</th>
			<th>Status</th>
			<th>Revenue</th>
			<th>Day Change</th>
			<th>Missing Report</th>
			<th>Recurring Lowest</th>
			<th>Reason</th>
		  </tr>
		</thead>
		<tbody>
		  {''.join(flagged_rows)}
		</tbody>
	  </table>
	</div>

	<div class="section">
	  <div class="collapsible-header">
		<span class="collapsible-toggle collapsed">▼</span>
		<h2 style="margin: 0;">Recurring Lowest Performers (last 30 days) ({days_with_tracked_data} days with tracked data)</h2>
	  </div>
	  <div class="collapsible-content">
		{_render_table(recurring_rows, [("Truck", "Truck"), ("Lowest Days", "LowestDays"), ("Report Day Revenue", "ReportDayRevenue")])}
	  </div>
	</div>

	<div class="section">
	  <div class="collapsible-header">
		<span class="collapsible-toggle collapsed">▼</span>
		<h2 style="margin: 0;">Revenue by Truck (Full Ranked Table)</h2>
	  </div>
	  <div class="collapsible-content">
		{_render_table(details_display, [("Truck", "Truck"), ("Revenue", "Revenue"), ("Sales", "Sales"), ("Avg Sale", "AvgSale"), ("Revenue Share (%)", "RevenueSharePct")])}
	  </div>
	</div>

	<div class="section">
	  <div class="collapsible-header">
		<span class="collapsible-toggle collapsed">▼</span>
		<h2 style="margin: 0;">Status and Reason by Truck</h2>
	  </div>
	  <div class="collapsible-content">
		{_render_table(status_display, [("Truck", "Truck"), ("Status", "Status"), ("Baseline Delta", "BaselineDelta"), ("Day Delta", "DayDelta"), ("Missing Report", "MissingReport"), ("Low Activity", "LowActivity"), ("Reason", "Reason")])}
	  </div>
	</div>

    <div class="section">
      <div class="collapsible-header">
		<span class="collapsible-toggle collapsed">▼</span>
		<h2 style="margin: 0;">Daily Worst Performing Truck(s) Summary</h2>
	  </div>
      <div class="collapsible-content">
		{_render_table(daily_lowest_display, [("Date", "Date"), ("Lowest Truck(s)", "Lowest Truck(s)"), ("Lowest Revenue", "Lowest Revenue"), ("Tied Trucks", "Tied Trucks")])}
	  </div>
    </div>
  </div>
</body>
</html>
"""

    return html


def handler(event, context):
    """AWS Lambda handler for generating the daily report."""
    config = dict(environ)

    missing = [
        key
        for key in ["GLUE_DB_NAME", "S3_BUCKET_NAME"]
        if key not in config
    ]
    if missing:
        raise RuntimeError(
            f"Missing required environment variables: {', '.join(missing)}"
        )

    report_date = date.today() - timedelta(days=1)
    html = generate_daily_report(
        glue_db_name=config["GLUE_DB_NAME"],
        s3_output=f"s3://{config['S3_BUCKET_NAME']}/athena-results/",
        report_date=report_date,
    )

    # Upload HTML to S3
    s3_client = boto3.client("s3")
    bucket_name = config["S3_BUCKET_NAME"]
    file_key = f"reports/daily_report_{report_date.strftime('%Y_%m_%d')}.html"
    s3_client.put_object(
        Bucket=bucket_name,
        Key=file_key,
        Body=html,
        ContentType="text/html",
    )

    return {
        "status": "ok",
        "reportDate": report_date.isoformat(),
    }
