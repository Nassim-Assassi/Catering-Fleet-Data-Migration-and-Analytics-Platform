# This module transforms extracted table data and saves transformed CSV files.

import sys

import pandas as pd

from paths import (
    EXTRACTED_PAYMENT_METHOD_DATA_FILE,
    EXTRACTED_TRANSACTION_DATA_FILE,
    EXTRACTED_TRUCK_DATA_FILE,
    TRANSFORMED_PAYMENT_METHOD_DATA_FILE,
    TRANSFORMED_TRANSACTION_DATA_FILE,
    TRANSFORMED_TRUCK_DATA_FILE,
)
from logging_config import configure_logging, get_logger

logger = get_logger(__name__)


TYPE_CHECKS = {
    "int": pd.api.types.is_integer_dtype,
    "numeric": pd.api.types.is_numeric_dtype,
    "str": pd.api.types.is_string_dtype,
}


def is_datetime_series(series: pd.Series) -> bool:
    """Return True when all values can be parsed as datetimes."""
    return pd.to_datetime(series, errors="coerce").notna().all()


def validate_fields(df: pd.DataFrame, expected_columns: dict[str, str], table_name: str) -> bool:
    """Validate required columns and logical data types for a table."""
    missing_columns = [
        col for col in expected_columns if col not in df.columns]
    if missing_columns:
        logger.error("%s missing columns: %s", table_name,
                     ", ".join(missing_columns))
        return False

    for column_name, expected_type in expected_columns.items():
        series = df[column_name]

        if expected_type == "datetime":
            if not is_datetime_series(series):
                logger.error("%s column '%s' must be datetime-like.",
                             table_name, column_name)
                return False
            continue

        type_check = TYPE_CHECKS.get(expected_type)
        if type_check is None:
            logger.error("Unsupported expected type '%s' for %s.%s",
                         expected_type, table_name, column_name)
            return False
        if not type_check(series):
            logger.error("%s column '%s' must be %s type.",
                         table_name, column_name, expected_type)
            return False

    return True


def validate_truck_table(df: pd.DataFrame) -> bool:
    """Validate DIM_Truck extracted data."""
    expected_columns = {
        "truck_id": "int",
        "truck_name": "str",
        "truck_description": "str",
        "has_card_reader": "int",
        "fsa_rating": "int",
    }
    return validate_fields(df, expected_columns, "DIM_Truck")


def validate_payment_method_table(df: pd.DataFrame) -> bool:
    """Validate DIM_Payment_Method extracted data."""
    expected_columns = {
        "payment_method_id": "int",
        "payment_method": "str",
    }
    return validate_fields(df, expected_columns, "DIM_Payment_Method")


def validate_transaction_table(df: pd.DataFrame) -> bool:
    """Validate FACT_Transaction extracted data."""
    expected_columns = {
        "transaction_id": "int",
        "truck_id": "int",
        "payment_method_id": "int",
        "total": "numeric",
        "at": "datetime",
    }
    return validate_fields(df, expected_columns, "FACT_Transaction")


def validate_payment_method_values(df: pd.DataFrame) -> pd.DataFrame:
    """Return payment method rows with valid values."""
    return df[df['payment_method'].isin(['card', 'cash'])].copy()


def validate_has_card_reader_values(df: pd.DataFrame) -> pd.DataFrame:
    """Return truck rows with valid has_card_reader values."""
    return df[df['has_card_reader'].isin([0, 1])].copy()


def validate_fsa_rating_values(df: pd.DataFrame) -> pd.DataFrame:
    """Return truck rows with valid fsa_rating values."""
    return df[df['fsa_rating'].isin([1, 2, 3, 4, 5])].copy()


def filter_invalid_truck_rows(df: pd.DataFrame) -> pd.DataFrame:
    """Drop DIM_Truck rows that violate field-value rules."""
    original_count = len(df)
    count = len(df)

    df = validate_has_card_reader_values(df)
    invalid_card_reader_count = count - len(df)
    count = len(df)

    df = validate_fsa_rating_values(df)
    invalid_fsa_rating_count = count - len(df)
    count = len(df)

    dropped_count = original_count - count

    if invalid_card_reader_count > 0:
        logger.warning(
            "DIM_Truck invalid has_card_reader values found in %s rows. Allowed values are: 0, 1.",
            invalid_card_reader_count,
        )
    if invalid_fsa_rating_count > 0:
        logger.warning(
            "DIM_Truck invalid fsa_rating values found in %s rows. Allowed values are: 1, 2, 3, 4, 5.",
            invalid_fsa_rating_count,
        )

    if dropped_count > 0:
        logger.warning(
            "DIM_Truck dropped %s invalid rows. Row count before: %s, after: %s.",
            dropped_count,
            original_count,
            count,
        )

    return df


def filter_invalid_payment_method_rows(df: pd.DataFrame) -> pd.DataFrame:
    """Drop DIM_Payment_Method rows with invalid payment_method values."""
    original_count = len(df)
    df = validate_payment_method_values(df)
    invalid_count = original_count - len(df)

    if invalid_count > 0:
        logger.warning(
            "DIM_Payment_Method invalid payment_method values found in %s rows. Allowed values are: card, cash.",
            invalid_count,
        )

    return df


def filter_invalid_transaction_rows(df: pd.DataFrame) -> pd.DataFrame:
    """Drop FACT_Transaction rows with invalid totals or timestamps."""
    original_count = len(df)

    df = df[df['total'] >= 0].copy()
    invalid_total_count = original_count - len(df)

    count = len(df)
    parsed_at = pd.to_datetime(df['at'], errors='coerce')
    df = df[parsed_at.notna()].copy()
    invalid_at_count = count - len(df)

    if invalid_total_count > 0:
        logger.warning(
            "FACT_Transaction invalid total values found in %s rows. Allowed values are non-negative.",
            invalid_total_count,
        )
    if invalid_at_count > 0:
        logger.warning(
            "FACT_Transaction invalid at timestamps found in %s rows.", invalid_at_count)

    return df


def has_card_reader_to_bool(df: pd.DataFrame) -> pd.DataFrame:
    """Convert has_card_reader values from 1/0 to boolean."""
    df['has_card_reader'] = df['has_card_reader'].map({1: True, 0: False})
    return df


def add_y_m_d_columns(df: pd.DataFrame, date_column: str = 'at') -> pd.DataFrame:
    """Add year/month/day columns derived from a date column."""
    df[date_column] = pd.to_datetime(df[date_column])
    df['year'] = df[date_column].dt.year
    df['month'] = df[date_column].dt.month
    df['day'] = df[date_column].dt.day
    return df


def transform_truck_data(df: pd.DataFrame) -> pd.DataFrame:
    """Apply DIM_Truck validations and transformations."""
    if not validate_truck_table(df):
        raise ValueError("DIM_Truck validation failed.")

    df = filter_invalid_truck_rows(df)
    return has_card_reader_to_bool(df)


def transform_payment_method_data(df: pd.DataFrame) -> pd.DataFrame:
    """Apply DIM_Payment_Method validations and transformations."""
    if not validate_payment_method_table(df):
        raise ValueError("DIM_Payment_Method validation failed.")

    df['payment_method'] = df['payment_method'].astype(
        str).str.strip().str.lower()
    return filter_invalid_payment_method_rows(df)


def transform_transaction_data(df: pd.DataFrame) -> pd.DataFrame:
    """Apply FACT_Transaction validations and transformations."""
    if not validate_transaction_table(df):
        raise ValueError("FACT_Transaction validation failed.")

    df = filter_invalid_transaction_rows(df)
    return add_y_m_d_columns(df, date_column='at')


def run_transform(
    truck_df: pd.DataFrame,
    payment_method_df: pd.DataFrame,
    transaction_df: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Transform extracted DIM_Truck, DIM_Payment_Method, and FACT_Transaction data."""
    logger.info("Transform module started.")

    logger.debug("Transforming DIM_Truck data...")
    transformed_truck_df = transform_truck_data(truck_df)
    logger.debug("Transforming DIM_Payment_Method data...")
    transformed_payment_method_df = transform_payment_method_data(
        payment_method_df)
    logger.debug("Transforming FACT_Transaction data...")
    transformed_transaction_df = transform_transaction_data(transaction_df)

    return transformed_truck_df, transformed_payment_method_df, transformed_transaction_df


if __name__ == "__main__":
    configure_logging(verbose=True)

    try:
        logger.debug("Reading extracted DIM_Truck data...")
        extracted_truck_df = pd.read_csv(EXTRACTED_TRUCK_DATA_FILE)
        logger.debug("Reading extracted DIM_Payment_Method data...")
        extracted_payment_method_df = pd.read_csv(
            EXTRACTED_PAYMENT_METHOD_DATA_FILE)
        logger.debug("Reading extracted FACT_Transaction data...")
        extracted_transaction_df = pd.read_csv(EXTRACTED_TRANSACTION_DATA_FILE)
    except Exception as e:
        logger.error(f"Failed to read extracted data: {e}")
        sys.exit(1)

    try:
        logger.debug("Transforming data...")
        (
            transformed_truck_df,
            transformed_payment_method_df,
            transformed_transaction_df,
        ) = run_transform(
            extracted_truck_df,
            extracted_payment_method_df,
            extracted_transaction_df,
        )
    except Exception as e:
        logger.error(f"Failed to transform data: {e}")
        sys.exit(1)

    try:
        logger.debug("Saving transformed DIM_Truck data...")
        transformed_truck_df.to_csv(TRANSFORMED_TRUCK_DATA_FILE, index=False)
        logger.debug("Saving transformed DIM_Payment_Method data...")
        transformed_payment_method_df.to_csv(
            TRANSFORMED_PAYMENT_METHOD_DATA_FILE,
            index=False,
        )
        logger.debug("Saving transformed FACT_Transaction data...")
        transformed_transaction_df.to_csv(
            TRANSFORMED_TRANSACTION_DATA_FILE, index=False)
        logger.info(
            "Transformed data saved to %s, %s, %s",
            TRANSFORMED_TRUCK_DATA_FILE,
            TRANSFORMED_PAYMENT_METHOD_DATA_FILE,
            TRANSFORMED_TRANSACTION_DATA_FILE,
        )
    except Exception as e:
        logger.error(f"Failed to save transformed data: {e}")
        sys.exit(1)
