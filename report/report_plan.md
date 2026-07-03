# HTML Report Plan

## Goal
Create a daily HTML report that gives a quick performance snapshot for the previous day, then highlights truck-level performance, unusual behaviour, and repeat underperformance patterns.

## Confirmed Decisions
- Run cadence: daily at 9:00 AM (scheduler setup handled separately)
- Report day: always previous day (partition day in Athena)
- Baseline window: trailing 7 days, excluding the report day (yesterday)
- Standout threshold: at least 30% above truck 7-day average revenue
- Underperformer threshold: at least 30% below truck 7-day average revenue
- Sharp-change threshold (secondary): at least +/-30% vs previous day, applied on top of baseline status
- Missing data rule: no transactions for previous day
- Bottom-pattern rule: lowest-revenue truck on at least 3 of last 7 days
- Output: one standalone HTML file written to report/
- Visual style: simple, clean utility style
- Low-activity rule: at least 30% below truck 7-day average sales count
- Tie rule for lowest ranking: include all tied trucks at the cutoff
- Truck roster for missing-data checks: active trucks only (if no active flag exists in DIM_Truck, treat trucks with >=1 transaction in the trailing 30 days as expected)
- Reason text: compact (1 short sentence per truck)

## Scope (aligned with dashboard concepts)
Use the same metric style already used in the dashboard module:
- Fleet-level totals (summary card style)
- Truck-level breakdown (table + ranked comparison)
- Time-based trends (daily trend context for each truck)

## Report Sections

### 0) Page Structure
- Page 1 = executive summary only (quick-read block at top of report)
- Detailed sections = placed below the summary on the same HTML page
- Summary should be readable in one screen/page without scrolling much

### 1) Fleet Snapshot (Previous Day)
- Total revenue across all trucks for previous day
- Total sales count across all trucks for previous day
- Optional context metric: change vs prior day (% up/down)

### 2) Revenue by Truck (Previous Day)
- Ranked table by truck revenue (high to low)
- Include: truck name, revenue, sales count, average sale value
- Include contribution to fleet total (%) for quick comparison

### 3) Standout and Underperforming Trucks
- Standout performer: trucks significantly above their own recent baseline
- Underperformer: trucks significantly below their own recent baseline
- Baseline window: trailing 7 days (excluding previous day)
- Output: short badge/label next to each flagged truck with reason

### 3.1) Combined Status and Colour Coding
- Compute two internal flags per truck:
	- Baseline performance flag (overperformer / neutral / underperformer)
	- Day-over-day sharp-change flag (sharp rise / none / sharp drop)
- Map those internal flags into one final display status (single colour shown in report)
- Blue: overperformer + sharp rise
- Green: overperformer
- Grey: does not meet any thresholds
- Orange: underperformer
- Red: underperformer + sharp drop
- Sharp rise/drop condition is evaluated against previous-day revenue change

### 4) Unusual Activity and Data Quality Flags
- Sharp change flag: previous-day revenue change beyond threshold vs prior day
- Missing-report flag: truck expected but has no previous-day transactions
- Low-activity flag: unusually low sales count vs baseline

### 5) Bottom-Performer Pattern Over Time
- Track repeated bottom performance via count of worst performances
- Rule: truck has the lowest daily revenue for 3 or more days out of the last 7
- If there is a tie at the lowest-revenue cutoff, include all tied trucks for that day
- Highlight trucks that meet this consistency rule

## Data and Metric Logic

### Core Inputs
- FACT_Transaction for totals, counts, day-level aggregation
- DIM_Truck for truck names and full truck roster (to detect missing reporters)

### Key Calculations
- Previous-day fleet revenue = SUM(total)/100
- Previous-day revenue by truck = SUM(total)/100 grouped by truck
- Previous-day sales by truck = COUNT(*) grouped by truck
- Average sale value by truck = AVG(total)/100
- Baseline per truck = mean revenue over trailing 7 days excluding report day
- Sales baseline per truck = mean sales count over trailing 7 days excluding report day
- Primary status (baseline threshold):
	- Overperformer: previous-day revenue >= baseline_mean * 1.30
	- Underperformer: previous-day revenue <= baseline_mean * 0.70
- Secondary sharp-change threshold (vs prior day):
	- Sharp rise: previous-day revenue >= prior_day_revenue * 1.30
	- Sharp drop: previous-day revenue <= prior_day_revenue * 0.70
- Internal evaluation model:
	- Evaluate baseline threshold and sharp-change threshold separately
	- Persist both internal flags for traceability/debugging
	- Display one final mapped colour status in the report table
- Final colour status:
	- Blue: overperformer and sharp rise
	- Green: overperformer only
	- Grey: neither overperformer nor underperformer
	- Orange: underperformer only
	- Red: underperformer and sharp drop
- Missing report: expected active truck (from active roster rule) absent from previous-day transactions
- Low-activity: previous-day sales_count <= sales_baseline_mean * 0.70

### Edge Case Rules
- If prior_day_revenue = 0, sharp-change flag = N/A (do not classify rise/drop)
- If baseline_mean = 0, baseline performance flag = N/A (do not classify over/under)
- If status cannot be classified due to N/A conditions, display grey with compact reason text

## HTML Layout (basic)
- Header: report date and generation timestamp
- Page 1 (Executive Summary):
	- 2 to 3 KPI cards (fleet revenue, total sales, day-over-day change)
	- Top 5 trucks and bottom 5 trucks by previous-day revenue
	- Flagged trucks only (missing data, red/orange/blue priority)
	- Mini bottom-pattern highlight (only trucks meeting consistency rule)
- Details Below (same page):
	- Full ranked truck table
	- Full flagged/status table with color chip (blue/green/grey/orange/red), mapped status, and compact reason text
	- Full bottom-performer trend details for last 7 days

## Implementation Steps
1. Build report wranglers in report/data_wranglers.py using dashboard query patterns.
   - add previous-day fleet metrics
   - add previous-day per-truck metrics
   - add trailing 7-day daily revenue/sales per truck
   - add DIM_Truck roster query for missing-report checks
2. Add aggregation and anomaly helper functions for baseline comparisons.
   - compute baseline and prior-day comparisons
   - compute low-activity flags
   - apply edge-case rules (N/A handling)
   - map internal flags to final colour status
3. Implement report generation in report/report_generator.py:
	- collect data
	- compute flags
	- render HTML template
	- write file output to report/daily_report_YYYY_MM_DD.html
4. Add simple styling for readability (cards, tables, status labels).
5. Validate against a sample day where:
	- at least one truck is missing
	- at least one truck is sharply down
	- one truck appears repeatedly in bottom tier
	- at least one truck hits baseline/prior-day zero edge case
6. Runtime behaviour:
	- always compute report for yesterday
	- no manual report-date override required

## Output
- Primary artifact: single HTML file in report/ (for example, daily_report_YYYY_MM_DD.html)
- Optional secondary artifact: CSV of flagged trucks for auditing

## Acceptance Criteria
- Report clearly shows previous-day fleet revenue and total sales.
- Report includes per-truck ranked revenue breakdown.
- Report flags unusual behaviour (drops and missing reporters).
- Report applies two-stage status logic (baseline + sharp-change) with final colour mapping.
- Report handles zero baseline and zero prior-day values without divide-by-zero errors.
- Report highlights recurring bottom performers over a trailing window.
- Report is readable without running the Streamlit dashboard.
