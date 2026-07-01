import sys
import io

import pandas as pd
from dotenv import load_dotenv
from os import environ
import sqlalchemy
import awswrangler as wr
from offset_helpers import get_offset_from_s3

from logging_config import configure_logging, get_logger

logger = get_logger(__name__)


def get_db_engine(config: dict) -> sqlalchemy.engine.base.Engine:
    # Create a SQLAlchemy engine
    engine = sqlalchemy.create_engine(
        f"mysql+pymysql://{config.get('DB_USER')}:{config.get('DB_PASSWORD')}@{config.get('DB_HOST')}/{config.get('DB_NAME')}")
    return engine


def extract_truck_data(engine: sqlalchemy.engine.base.Engine) -> pd.DataFrame:
    query = """
    SELECT *      
    FROM DIM_Truck dt
"""

    # Read data from the MySQL database into a pandas DataFrame
    df = pd.read_sql(query, engine)
    logger.info(f"Extracted {len(df)} rows from the database.")

    return df


def extract_payment_method_data(engine: sqlalchemy.engine.base.Engine) -> pd.DataFrame:
    query = """
    SELECT *      
    FROM DIM_Payment_Method dpm
"""

    # Read data from the MySQL database into a pandas DataFrame
    df = pd.read_sql(query, engine)
    logger.info(f"Extracted {len(df)} rows from the database.")

    return df


def extract_transaction_data(engine: sqlalchemy.engine.base.Engine, offset: int) -> pd.DataFrame:
    if offset:
        # Build query that filters to only new transactions (ID > offset)
        query = f"""
    SELECT *      
    FROM FACT_Transaction ft
    WHERE transaction_id > {offset}
    ORDER BY transaction_id ASC
"""
    else:
        query = """
    SELECT *      
    FROM FACT_Transaction ft
    ORDER BY transaction_id ASC
"""

    # Read data from the MySQL database into a pandas DataFrame
    df = pd.read_sql(query, engine)
    logger.info(f"Extracted {len(df)} new transactions from the database.")

    if df.empty:
        raise ValueError(
            "No new transactions to process. All IDs already parsed.")

    return df


def run_extract(engine: sqlalchemy.engine.base.Engine, current_offset: int) -> tuple:

    # Read data from the MySQL database into a pandas DataFrame
    truck_df = extract_truck_data(engine)
    payment_method_df = extract_payment_method_data(engine)

    # Extract and filter transactions
    transaction_df = extract_transaction_data(engine, current_offset)

    # Get new offset (the most recent transaction ID)
    new_offset = transaction_df['transaction_id'].max()

    return truck_df, payment_method_df, transaction_df, new_offset


if __name__ == "__main__":
    configure_logging(verbose=True)
    from paths import (
        EXTRACTED_PAYMENT_METHOD_DATA_FILE,
        EXTRACTED_TRANSACTION_DATA_FILE,
        EXTRACTED_TRUCK_DATA_FILE,
    )

    # Load environment variables from .env file
    load_dotenv()
    config: dict[str, str] = dict(environ)

    engine = None

    try:
        logger.debug("Creating database engine...")
        engine = get_db_engine(config)
    except Exception as e:
        logger.error(f"Failed to create database engine: {e}")
        sys.exit(1)

    try:
        logger.debug("Extracting data from database...")
        s3_bucket_name = config.get("S3_BUCKET_NAME")
        if not s3_bucket_name:
            raise ValueError("S3_BUCKET_NAME is not set in the configuration.")
        current_offset = get_offset_from_s3(s3_bucket_name)
        truck_df, payment_method_df, transaction_df, new_offset = run_extract(
            engine, current_offset)
    except Exception as e:
        logger.error(f"Failed to extract data: {e}")
        sys.exit(1)
    finally:
        if engine:
            engine.dispose()

    try:
        logger.debug("Saving extracted data to CSV...")
        truck_df.to_csv(EXTRACTED_TRUCK_DATA_FILE, index=False)
        payment_method_df.to_csv(
            EXTRACTED_PAYMENT_METHOD_DATA_FILE, index=False)
        transaction_df.to_csv(EXTRACTED_TRANSACTION_DATA_FILE, index=False)
        logger.info(
            f"Data saved to {EXTRACTED_TRUCK_DATA_FILE}, {EXTRACTED_PAYMENT_METHOD_DATA_FILE}, {EXTRACTED_TRANSACTION_DATA_FILE}")
    except Exception as e:
        logger.error(f"Failed to save data to CSV: {e}")
        sys.exit(1)
