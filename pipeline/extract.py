# This module is responsible for extracting data from the MySQL RDS instance.

import sys

import pandas as pd
from dotenv import load_dotenv
from os import environ
from paths import EXTRACTED_TRUCK_DATA_FILE, EXTRACTED_PAYMENT_METHOD_DATA_FILE, EXTRACTED_TRANSACTION_DATA_FILE
import sqlalchemy

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


def extract_transaction_data(engine: sqlalchemy.engine.base.Engine) -> pd.DataFrame:
    query = """
    SELECT *      
    FROM FACT_Transaction ft
"""

    # Read data from the MySQL database into a pandas DataFrame
    df = pd.read_sql(query, engine)
    logger.info(f"Extracted {len(df)} rows from the database.")

    return df


def run_extract(engine: sqlalchemy.engine.base.Engine) -> pd.DataFrame:

    # Read data from the MySQL database into a pandas DataFrame
    truck_df = extract_truck_data(engine)
    payment_method_df = extract_payment_method_data(engine)
    transaction_df = extract_transaction_data(engine)

    return truck_df, payment_method_df, transaction_df


if __name__ == "__main__":
    configure_logging(verbose=True)

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
        truck_df, payment_method_df, transaction_df = run_extract(engine)
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
