"""Shared paths for pipeline scripts and modules."""

from pathlib import Path

REPO_DIR = Path(__file__).resolve().parent

EXTRACTED_TRUCK_DATA_FILE = REPO_DIR / "extracted_truck_data.csv"
EXTRACTED_PAYMENT_METHOD_DATA_FILE = REPO_DIR / \
    "extracted_payment_method_data.csv"
EXTRACTED_TRANSACTION_DATA_FILE = REPO_DIR / "extracted_transaction_data.csv"
TRANSFORMED_TRUCK_DATA_FILE = REPO_DIR / "transformed_truck_data.csv"
TRANSFORMED_PAYMENT_METHOD_DATA_FILE = REPO_DIR / \
    "transformed_payment_method_data.csv"
TRANSFORMED_TRANSACTION_DATA_FILE = REPO_DIR / "transformed_transaction_data.csv"
