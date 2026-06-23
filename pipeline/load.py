
import awswrangler as wr
from logging_config import configure_logging, get_logger

logger = get_logger(__name__)


def upload_to_s3(df, file_path, bucket_name, object_name):
    """
    Uploads a file to an S3 bucket using awswrangler.
    data is partitioned by the day from the 'at' column in the DataFrame.
    """
    try:

        # Write the DataFrame to S3 in Parquet format, partitioned by day
        wr.s3.to_parquet(
            df=df,
            path=f"s3://{bucket_name}/{object_name}",
            dataset=True,
            partition_cols=['at'],
            mode='overwrite'
        )
        logger.info(
            f"Successfully uploaded {file_path} to s3://{bucket_name}/{object_name}")
    except Exception as e:
        logger.error(f"Failed to upload {file_path} to S3: {e}")
        raise


def upload_transaction_data():
    """Uploads transaction data to S3."""

    raise NotImplementedError


if __name__ == "__main__":
    configure_logging(verbose=True)

    upload_transaction_data()
