import awswrangler as wr
import pandas as pd
from logging_config import get_logger

logger = get_logger(__name__)


def get_offset_from_s3(bucket_name: str) -> int:
    """Get the most recent transaction ID (offset) from S3."""
    path = f"s3://{bucket_name}/offset.json"
    if not wr.s3.does_object_exist(path):
        logger.info(
            "No existing offset.json file found, starting from beginning.")
        return 0

    try:
        offset_data = wr.s3.read_json(
            path=path,
            lines=True,
        )
        if offset_data.empty or "offset" not in offset_data.columns:
            raise ValueError("offset.json is empty or missing 'offset'.")

        offset = offset_data.iloc[0]["offset"]
        logger.info(f"Read offset from S3: {offset}")
        return offset
    except ValueError:
        logger.warning(
            "offset.json is not a valid integer. Resetting offset to 0 and continuing.")
        return 0


def save_offset_to_s3(bucket_name: str, offset: int) -> None:
    """Save the most recent transaction ID (offset) to S3."""
    wr.s3.to_json(
        df=pd.DataFrame({"offset": [offset]}),
        path=f"s3://{bucket_name}/offset.json",
        orient="records",
        lines=True,
    )
    logger.info(f"Saved offset to S3: {offset}")
