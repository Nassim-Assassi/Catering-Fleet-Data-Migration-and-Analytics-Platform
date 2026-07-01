
import sys
import pandas as pd

from dotenv import load_dotenv
from os import environ
import awswrangler as wr
from logging_config import configure_logging, get_logger

logger = get_logger(__name__)


def upload_truck_data_to_s3(bucket_name, df):
    """
    Uploads the transformed truck data to an S3 bucket using awswrangler.
    """
    wr.s3.to_parquet(
        df=df,
        index=False,
        path=f"s3://{bucket_name}/Food_Trucks/DIM_Truck",
        dataset=True,
        mode="overwrite",
    )


def upload_payment_method_data_to_s3(bucket_name, df):
    """
    Uploads the transformed payment method data to an S3 bucket using awswrangler.
    """
    wr.s3.to_parquet(
        df=df,
        index=False,
        path=f"s3://{bucket_name}/Food_Trucks/DIM_Payment_Method",
        dataset=True,
        mode="overwrite",
    )


def upload_transaction_data_to_s3(bucket_name, df):
    """
    Uploads the transformed transaction data to an S3 bucket using awswrangler.
    Data is partitioned by year, month, and day for efficient querying.
    """
    if df.empty:
        raise ValueError(
            "Transaction DataFrame is empty. Pipeline will not run.")
    wr.s3.to_parquet(
        df=df,
        index=False,
        path=f"s3://{bucket_name}/Food_Trucks/FACT_Transaction",
        dataset=True,
        mode="append",
        partition_cols=['year', 'month', 'day'],
    )


def run_load(
        config,
        truck_df: pd.DataFrame,
        payment_method_df: pd.DataFrame,
        transaction_df: pd.DataFrame,):
    """
    Uploads the transformed data to an S3 bucket.
    """
    bucket_name = config.get("S3_BUCKET_NAME")
    if not bucket_name:
        raise ValueError("S3_BUCKET_NAME is not set in the configuration.")

    try:
        upload_truck_data_to_s3(bucket_name, truck_df)
    except Exception as e:
        raise Exception(f"Failed to upload truck data to S3: {e}")
    try:
        upload_payment_method_data_to_s3(bucket_name, payment_method_df)
    except Exception as e:
        raise Exception(f"Failed to upload payment method data to S3: {e}")
    try:
        upload_transaction_data_to_s3(bucket_name, transaction_df)
    except Exception as e:
        raise Exception(f"Failed to upload transaction data to S3: {e}")


if __name__ == "__main__":
    configure_logging(verbose=True)
    from paths import (
        TRANSFORMED_PAYMENT_METHOD_DATA_FILE,
        TRANSFORMED_TRANSACTION_DATA_FILE,
        TRANSFORMED_TRUCK_DATA_FILE,
    )

    load_dotenv()
    config: dict[str, str] = dict(environ)

    try:
        logger.debug("Reading transformed DIM_Truck data...")
        transformed_truck_df = pd.read_csv(TRANSFORMED_TRUCK_DATA_FILE)
        logger.debug("Reading transformed DIM_Payment_Method data...")
        transformed_payment_method_df = pd.read_csv(
            TRANSFORMED_PAYMENT_METHOD_DATA_FILE
        )
        logger.debug("Reading transformed FACT_Transaction data...")
        transformed_transaction_df = pd.read_csv(
            TRANSFORMED_TRANSACTION_DATA_FILE)
    except Exception as e:
        logger.error(f"Failed to read transformed data: {e}")
        sys.exit(1)

    try:
        logger.debug("Uploading transformed data to S3...")
        run_load(config,
                 truck_df=transformed_truck_df,
                 payment_method_df=transformed_payment_method_df,
                 transaction_df=transformed_transaction_df
                 )
    except Exception as e:
        logger.error(f"Failed to upload transformed data to S3: {e}")
        sys.exit(1)
