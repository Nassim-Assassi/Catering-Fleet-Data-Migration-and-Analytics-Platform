# This module is responsible for extracting data from the MySQL RDS instance.

import sys

import pandas as pd
from dotenv import load_dotenv
from os import environ
from paths import EXTRACTED_DATA_FILE
import sqlalchemy

from logging_config import configure_logging, get_logger

logger = get_logger(__name__)


def get_db_engine(config: dict):
    # Create a SQLAlchemy engine
    engine = sqlalchemy.create_engine(
        f"mysql+pymysql://{config.get('DB_USER')}:{config.get('DB_PASSWORD')}@{config.get('DB_HOST')}/{config.get('DB_NAME')}")
    return engine


def run_extract(engine: sqlalchemy.engine.base.Engine) -> pd.DataFrame:

    query = """
    SELECT ft.transaction_id,ft.total,ft.at,dpm.payment_method, dt.truck_name, dt.truck_description,dt.has_card_reader,dt.fsa_rating      
    FROM FACT_Transaction ft 
    JOIN DIM_Payment_Method dpm ON ft.payment_method_id = dpm.payment_method_id
    JOIN DIM_Truck dt ON ft.truck_id = dt.truck_id
"""

    # Read data from the MySQL database into a pandas DataFrame
    df = pd.read_sql(query, engine)
    logger.info(f"Extracted {len(df)} rows from the database.")

    return df


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
        df = run_extract(engine)
    except Exception as e:
        logger.error(f"Failed to extract data: {e}")
        sys.exit(1)
    finally:
        if engine:
            engine.dispose()

    try:
        logger.debug("Saving extracted data to CSV...")
        df.to_csv(EXTRACTED_DATA_FILE, index=False)
        logger.info(f"Data saved to {EXTRACTED_DATA_FILE}")
    except Exception as e:
        logger.error(f"Failed to save data to CSV: {e}")
        sys.exit(1)
