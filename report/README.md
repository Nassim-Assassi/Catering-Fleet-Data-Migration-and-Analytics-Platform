# Daily Fleet Report Generator

Generates a daily HTML performance report for the food truck fleet from Athena data. The report covers the previous day's revenue and sales, flags standout/underperforming/missing trucks, and highlights recurring bottom performers.

It includes:

- **Executive Summary**: fleet revenue, total sales, day-over-day change, and top/bottom 5 trucks by revenue.
- **Flagged Trucks**: trucks that are overperforming, underperforming, missing a report, or low-activity, each with a colour-coded status chip and a short reason.
- **Recurring Lowest Performers**: trucks that were the lowest daily revenue for 3+ of the last 7 days.
- **Full Ranked Table**: revenue, sales, average sale value, and revenue share per truck.
- **Status and Reason by Truck**: baseline/day-over-day deltas, missing-report and low-activity flags, and reason text for every truck.
- **Daily Worst Performing Truck(s) Summary**: lowest-revenue truck(s) per day over the tracked window (including ties).

See [report_plan.md](report_plan.md) for the full design/thresholds behind the flags and status colours.

## Project Files

- `report_generator.py`: Builds report data into HTML, and the `handler` function used as the AWS Lambda entry point (uploads the HTML to S3 under `reports/`).
- `report_data_wranglers.py`: Athena queries and calculations (fleet/truck metrics, baselines, flags, status colours) used by the report.
- `local_report_generator.py`: Runs the report generator locally and writes the HTML to a file instead of uploading to S3.
- `requirements.txt`: Python dependencies for the report generator.
- `dockerfile`: builds the Lambda container image (based on `public.ecr.aws/lambda/python:latest`).
- `scripts/deploy_report_generator.sh`: builds the report generator Lambda image for `linux/x86_64` and pushes it to ECR.
- `report_plan.md`: design notes for report sections, thresholds, and status colour mapping.

## Prerequisites

Before running the report generator, make sure you have:

- Python 3.10+.
- Access to AWS Athena in the target account.
- Valid AWS credentials configured locally (for example via `aws configure`, SSO, or environment variables).
- A `.env` file providing these environment variables:
	- `GLUE_DB_NAME`: the Glue/Athena database to query.
	- `S3_BUCKET_NAME`: the bucket used for Athena query results (`s3://<bucket>/athena-results/`) and, when run as a Lambda, for the uploaded report (`s3://<bucket>/reports/`).

The app expects these tables to exist in `GLUE_DB_NAME` and be queryable:

- `FACT_Transaction`
- `DIM_Truck`

## Install Dependencies

From this `report` directory, create/activate a virtual environment, then install packages:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run Locally

`local_report_generator.py` calls `load_dotenv()` on startup, so place a `.env` file (containing at least `GLUE_DB_NAME` and `S3_BUCKET_NAME`) somewhere `python-dotenv` can find it, such as this `report` directory or a parent directory.

From the `report` folder, run:

```bash
python local_report_generator.py
```

The report is always generated for the previous day and written to `daily_report_YYYY_MM_DD.html` in the current directory. Open the file in a browser to view it.

## Run with Docker / Deploy to Lambda

This folder includes:

- `dockerfile`: builds a Lambda container image with `report_generator.py` and `report_data_wranglers.py`, entry point `report_generator.handler`.
- `scripts/deploy_report_generator.sh`: builds the report generator image for `linux/x86_64` (required for Lambda) and pushes it to the ECR repository provisioned by Terraform.

From the repository root, build and push the image with:

```bash
bash scripts/deploy_report_generator.sh
```

This reads `AWS_REGION` and `INFRASTRUCTURE_NAME` from `terraform/terraform.tfvars`, logs in to ECR, and pushes the image tagged `latest`.

After the image is pushed, set `deploy_report_generator_lambda = "yes"` and run `terraform apply` from the `terraform` directory to create or update the Lambda function. It is invoked with `GLUE_DB_NAME` and `S3_BUCKET_NAME` environment variables already set, and uploads the generated HTML to `s3://<bucket>/reports/daily_report_YYYY_MM_DD.html`.

## How It Works

1. `prepare_report_data` (in `report_data_wranglers.py`) queries Athena for:
	 - Previous day's fleet totals and per-truck revenue/sales/average sale value.
	 - A trailing baseline window (7 days, excluding the report day) per truck.
	 - The full truck roster, to detect trucks missing a report.
	 - Daily lowest-revenue truck(s) over a tracked window, to detect recurring bottom performers.
2. Baseline and day-over-day thresholds (±30%) are applied to classify each truck as overperforming, underperforming, neutral, or N/A (when a baseline or prior-day value is zero), and mapped to a single status colour (blue/green/grey/orange/red).
3. `report_generator.py` renders the computed data into a single self-contained HTML page with summary cards, collapsible detail sections, and status chips.

## Common Issues

- `Missing required environment variables: GLUE_DB_NAME, S3_BUCKET_NAME` (raised by `handler`):
	- Add a `.env` file (local run) or Lambda environment variables with `GLUE_DB_NAME` and `S3_BUCKET_NAME`.
- `Unable to locate credentials`:
	- Configure AWS credentials/profile and retry.
- Athena access errors (`AccessDeniedException`, database/table not found):
	- Verify IAM permissions and that the database/tables exist in the selected AWS account/region.
- Empty or `No data available.` tables:
	- Check whether transactions exist for the report date (previous day) and the trailing baseline window.
- `docker buildx` errors when running `scripts/deploy_report_generator.sh`:
	- Ensure Docker Buildx is available (`docker buildx version`) and you are logged in to the correct AWS account/region.
