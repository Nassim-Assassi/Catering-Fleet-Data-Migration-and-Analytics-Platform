# This module is responsible for transforming extracted data and saving it as a parquet file.

import sys

import pandas as pd

from paths import EXTRACTED_DATA_FILE, TRANSFORMED_DATA_FILE
from logging_config import configure_logging, get_logger

logger = get_logger(__name__)


def validate_extracted_data_types(df: pd.DataFrame) -> bool:
    """Validate the extracted data for expected columns and types."""
    expected_columns = {
        'transaction_id': 'int64',
        'total': 'float64',
        'at': 'datetime64[us]',
        'payment_method': 'str',
        'truck_name': 'str',
        'truck_description': 'str',
        'has_card_reader': 'int64',  # Assuming 1/0 representation
        'fsa_rating': 'int64',  # Assuming integer representation
    }

    for col, dtype in expected_columns.items():
        if col not in df.columns:
            logger.error(f"Missing expected column: {col}")
            return False
        if str(df[col].dtype) != dtype:
            logger.error(
                f"Column '{col}' has unexpected type: {df[col].dtype}, expected: {dtype}")
            return False

    logger.info("Extracted data validation passed.")
    return True


def has_card_reader_to_bool(df: pd.DataFrame) -> pd.DataFrame:
    """Convert 'has_card_reader' column from 1/0 to boolean True/False."""
    df['has_card_reader'] = df['has_card_reader'].map({1: True, 0: False})
    return df


def validate_payment_method(df: pd.DataFrame) -> pd.DataFrame:
    """Return rows with valid payment methods."""
    return df[df['payment_method'].isin(['card', 'cash'])].copy()


def validate_has_card_reader(df: pd.DataFrame) -> pd.DataFrame:
    """Return rows with valid has_card_reader values."""
    return df[df['has_card_reader'].isin([0, 1])].copy()


def validate_fsa_rating(df: pd.DataFrame) -> pd.DataFrame:
    """Return rows with valid fsa_rating values."""
    return df[df['fsa_rating'].isin([1, 2, 3, 4, 5])].copy()


def filter_invalid_rows(df: pd.DataFrame) -> pd.DataFrame:
    """Drop rows that violate field-value rules and log a summary."""
    original_count = len(df)
    count = len(df)

    # Apply validators sequentially
    df = validate_payment_method(df)
    invalid_payment_count = count - len(df)
    count = len(df)

    df = validate_has_card_reader(df)
    invalid_card_reader_count = count - len(df)
    count = len(df)

    df = validate_fsa_rating(df)
    invalid_fsa_rating_count = count - len(df)
    count = len(df)

    dropped_count = original_count - count

    if invalid_payment_count > 0:
        logger.warning(
            "Invalid payment_method values found in %s rows. Allowed values are: card, cash.",
            invalid_payment_count,
        )
    if invalid_card_reader_count > 0:
        logger.warning(
            "Invalid has_card_reader values found in %s rows. Allowed values are: 0, 1.",
            invalid_card_reader_count,
        )
    if invalid_fsa_rating_count > 0:
        logger.warning(
            "Invalid fsa_rating values found in %s rows. Allowed values are: 1, 2, 3, 4, 5.",
            invalid_fsa_rating_count,
        )

    if dropped_count > 0:
        logger.warning(
            "Dropped %s invalid rows. Row count before: %s, after: %s.",
            dropped_count,
            original_count,
            count,
        )

    return df


def transform_data(df: pd.DataFrame) -> pd.DataFrame:
    """Transform the extracted data"""

    logger.info("Transform module started.")

    if not validate_extracted_data_types(df):
        logger.error("Data validation failed. Exiting transformation.")
        sys.exit(1)

    df = filter_invalid_rows(df)
    df = has_card_reader_to_bool(df)
    return df


if __name__ == "__main__":
    configure_logging(verbose=True)

    try:
        logger.debug(f"Reading extracted data from {EXTRACTED_DATA_FILE}...")
        extracted_df = pd.read_csv(EXTRACTED_DATA_FILE, parse_dates=['at'])
    except Exception as e:
        logger.error(f"Failed to read extracted data: {e}")
        sys.exit(1)

    transformed_df = transform_data(extracted_df)

    try:
        logger.debug(f"Saving transformed data to {TRANSFORMED_DATA_FILE}...")
        transformed_df.to_csv(TRANSFORMED_DATA_FILE, index=False)
        logger.info(f"Transformed data saved to {TRANSFORMED_DATA_FILE}")
    except Exception as e:
        logger.error(f"Failed to save transformed data: {e}")
        sys.exit(1)
