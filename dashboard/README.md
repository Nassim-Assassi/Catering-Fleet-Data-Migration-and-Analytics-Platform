# Food Truck Analytics Dashboard

This dashboard is a Streamlit app that queries AWS Athena and visualizes monthly food truck performance.

It includes four views:

- Revenue Summary: total revenue, revenue per truck, and average sale value per truck.
- Revenue Trends: daily and hourly revenue trends by truck.
- Popularity Summary: total sales and sales per truck.
- Popularity Trends: daily and hourly sales trends by truck.

## Project Files

- `dashboard.py`: Streamlit UI and chart rendering.
- `data_wranglers.py`: Athena queries used by the dashboard.
- `requirements.txt`: Python dependencies for this dashboard.

## Prerequisites

Before running the dashboard, make sure you have:

- Python 3.10+.
- Access to AWS Athena in the target account.
- Valid AWS credentials configured locally (for example via `aws configure`, SSO, or environment variables).
- Access to this Athena database used in the code:
	- `c24-nassim-food-trucks-glue-database`

The app expects these tables to exist and be queryable:

- `FACT_Transaction`
- `DIM_Truck`

## Install Dependencies

From this `dashboard` directory, create/activate a virtual environment, then install packages:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run the Dashboard

Start Streamlit from the `dashboard` folder:

```bash
streamlit run dashboard.py
```

Streamlit will print a local URL (usually `http://localhost:8501`). Open it in your browser.

## Run with Docker

This folder includes:

- `dockerfile`: builds the dashboard image.
- `docker-compose.yml`: builds/runs the dashboard service and maps port `8501`.

The compose service uses:

- `build.context: .`
- `build.dockerfile: dockerfile`
- `env_file: ../.env`
- `ports: 8501:8501`

From the `dashboard` directory, run:

```bash
docker compose up --build
```

Then open:

```text
http://localhost:8501
```

To stop the container:

```bash
docker compose down
```

## How To Use

Use the left sidebar to control what you see:

1. Choose a dashboard page:
	 - Revenue Summary
	 - Revenue Trends
	 - Popularity Summary
	 - Popularity Trends
2. Select a `Year`.
3. Select a `Month`.
4. Use the truck colour legend in the sidebar to map chart colors to truck names.

The charts and metrics refresh automatically when you change page/month/year.

## Data Refresh Behavior

Query results are cached in Streamlit for 30 minutes (`TTL = 1800` seconds) to reduce repeated Athena calls.

If underlying data changes and you need an immediate refresh:

- Wait for cache expiry, or
- Restart the Streamlit app.

## Common Issues

- `Unable to locate credentials`:
	- Configure AWS credentials/profile and retry.
- Athena access errors (`AccessDeniedException`, database/table not found):
	- Verify IAM permissions and that the database/tables exist in the selected AWS account/region.
- Empty charts:
	- Check whether data exists for the selected month/year.
- Port already in use:
	- Run on a different port, for example:
		```bash
		streamlit run dashboard.py --server.port 8502
		```