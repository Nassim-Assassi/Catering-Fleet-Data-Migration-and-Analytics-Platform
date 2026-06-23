"""Shared paths for pipeline scripts and modules."""

from pathlib import Path

PIPELINE_DIR = Path(__file__).resolve().parent

EXTRACTED_DATA_FILE = PIPELINE_DIR / "extracted_data.csv"
TRANSFORMED_DATA_FILE = PIPELINE_DIR / "transformed_data.csv"
