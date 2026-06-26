# ETL Pipeline

A Python-based Extract-Transform-Load (ETL) pipeline that extracts food truck transaction data from MySQL, validates and transforms it, and loads it to AWS.

## Overview

The pipeline processes food truck transaction data through three stages:

1. **Extract** — Read data from MySQL RDS database (trucks, payment methods, transactions)
2. **Transform** — Validate and clean data (type checking, format validation)
3. **Load** — Push transformed data to AWS (S3/Glue database)

## Prerequisites

- Python 3.8+
- MySQL RDS database with data loaded
- AWS credentials configured (for loading to AWS)
- Docker (optional, for containerized execution)

## Installation

### Local Setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Create a `.env` file in the workspace root with:
   ```
   DB_USER=<mysql_username>
   DB_PASSWORD=<mysql_password>
   DB_HOST=<mysql_host>
   DB_NAME=<database_name>
   AWS_ACCESS_KEY_ID=<your_key>
   AWS_SECRET_ACCESS_KEY=<your_secret>
   AWS_S3_BUCKET=<s3_bucket_name>
   ```

## Usage

### Run Locally

```bash
cd pipeline
python pipeline.py
```

The script will:
- Connect to MySQL and extract data
- Transform and validate all tables
- Load processed data to AWS
- Write status logs to the console

### Run with Docker

```bash
cd pipeline
docker-compose up
```

Docker will build an image, apply environment variables from `.env`, and run the pipeline in a container.

## Output

After successful execution:
- Extracted data is cached in CSV files (extracted_*.csv)
- Transformed data is saved to CSV files (transformed_*.csv)
- Data is loaded to AWS Glue database: `c24-nassim-food-trucks-glue-database`

## Modules

- **extract.py** — Connects to MySQL, queries truck/payment/transaction tables
- **transform.py** — Validates data types, handles missing values, formats dates
- **load.py** — Uploads transformed data to AWS S3 and Glue
- **logging_config.py** — Configures debug and error logging
- **paths.py** — Defines file paths for extracted and transformed data

## Troubleshooting

- **Database connection fails** — Check DB_HOST, DB_USER, DB_PASSWORD in .env
- **AWS upload fails** — Verify AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY are set
- **Data validation errors** — Review logs for which columns failed type checks in transform.py