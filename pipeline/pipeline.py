import sys

import awswrangler as wr
from dotenv import load_dotenv
from os import environ

from logging_config import configure_logging, get_logger
from extract import get_db_engine, run_extract
from offset_helpers import get_offset_from_s3, save_offset_to_s3
from load import run_load
from transform import run_transform
logger = get_logger(__name__)


def run_pipeline(config: dict[str, str]) -> None:

    engine = None

    try:
        engine = get_db_engine(config)
        s3_bucket_name = config.get("S3_BUCKET_NAME")
        if not s3_bucket_name:
            raise ValueError("S3_BUCKET_NAME is not set in the configuration.")
        current_offset = get_offset_from_s3(s3_bucket_name)
        truck_df, payment_method_df, transaction_df, new_offset = run_extract(
            engine, current_offset)
        truck_df, payment_method_df, transaction_df = run_transform(
            truck_df, payment_method_df, transaction_df
        )
        run_load(config, truck_df, payment_method_df, transaction_df)

        # Save offset only after successful load
        save_offset_to_s3(s3_bucket_name, new_offset)
    finally:
        if engine:
            engine.dispose()


if __name__ == "__main__":
    configure_logging(verbose=False)

    # Load environment variables from .env file
    load_dotenv()
    config: dict[str, str] = dict(environ)

    try:
        run_pipeline(config)
    except Exception as e:
        logger.error(f"Pipeline failed: {e}")
        sys.exit(1)
