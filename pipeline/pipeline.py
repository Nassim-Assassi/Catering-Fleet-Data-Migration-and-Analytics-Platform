import sys

from dotenv import load_dotenv
from os import environ

from logging_config import configure_logging, get_logger
from extract import get_db_engine, run_extract
from transform import transform_data

logger = get_logger(__name__)

if __name__ == "__main__":
    configure_logging(verbose=True)

    # laod environment variables from .env file

    # Load environment variables from .env file
    load_dotenv()
    config: dict[str, str] = dict(environ)

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
        df = run_extract(engine)
    except Exception as e:
        logger.error(f"Failed to extract data: {e}")
        sys.exit(1)
    finally:
        if engine:
            engine.dispose()

    # run transform
    try:
        logger.debug("Transforming data...")
        transformed_df = transform_data(df)
    except Exception as e:
        logger.error(f"Failed to transform data: {e}")
        sys.exit(1)
