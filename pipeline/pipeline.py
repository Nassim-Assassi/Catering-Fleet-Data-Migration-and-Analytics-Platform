import sys

from dotenv import load_dotenv
from os import environ

from logging_config import configure_logging, get_logger
from extract import get_db_engine, run_extract
from load import run_load
from transform import run_transform

logger = get_logger(__name__)


def run_pipeline(config: dict[str, str]) -> None:

    # create a database engine
    engine = None

    try:
        logger.debug("Creating database engine...")
        engine = get_db_engine(config)
    except Exception as e:
        logger.error(f"Failed to create database engine: {e}")
        sys.exit(1)

    # run extract
    try:
        logger.debug("Extracting data from database...")
        truck_df, payment_method_df, transaction_df = run_extract(engine)
    except Exception as e:
        logger.error(f"Failed to extract data: {e}")
        sys.exit(1)
    finally:
        if engine:
            engine.dispose()

    # run transform
    try:
        logger.debug("Transforming data...")
        truck_df, payment_method_df, transaction_df = run_transform(
            truck_df, payment_method_df, transaction_df
        )
    except Exception as e:
        logger.error(f"Failed to transform data: {e}")
        sys.exit(1)

    try:
        logger.debug("Loading data...")
        run_load(config, truck_df, payment_method_df, transaction_df)
    except Exception as e:
        logger.error(f"Failed to load data: {e}")
        sys.exit(1)


if __name__ == "__main__":
    configure_logging(verbose=False)

    # Load environment variables from .env file
    load_dotenv()
    config: dict[str, str] = dict(environ)

    run_pipeline(config)
