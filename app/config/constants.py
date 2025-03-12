"""
Application Constants and Configuration Values

This module contains centralized configuration values for the entire application.
It helps maintain clean code by avoiding hardcoded values scattered throughout the codebase.
"""
from pathlib import Path
import os

# Application paths
APP_DIR = Path(__file__).parent.parent
ROOT_DIR = APP_DIR.parent
DATA_DIR = ROOT_DIR / "data"

# LOINC configuration
LOINC_DATA_DIR = DATA_DIR / "Loinc_2.80" / "LoincTableCore"
LOINC_CSV_PATH = LOINC_DATA_DIR / "LoincTableCore.csv"
LOINC_INDEX_PATH = DATA_DIR / "loinc_enhanced_index.json"

# Ensure necessary directories exist
DATA_DIRS = [
    DATA_DIR,
    LOINC_DATA_DIR,
]

for directory in DATA_DIRS:
    os.makedirs(directory, exist_ok=True) 