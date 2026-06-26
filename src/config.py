"""
config.py — Centralised, environment-agnostic configuration.

All path resolution is computed relative to the repository root so that
the application works correctly regardless of the machine or container it
runs inside.  No hard-coded absolute paths appear anywhere in this file.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

# ---------------------------------------------------------------------------
# Root anchor – always the parent of src/
# ---------------------------------------------------------------------------
ROOT_DIR: Path = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------------
# Sub-directory paths (created lazily when first needed)
# ---------------------------------------------------------------------------
DATA_DIR: Path = ROOT_DIR / "data"
DATABASE_DIR: Path = ROOT_DIR / "database"
LOGS_DIR: Path = ROOT_DIR / "logs"

# Ensure runtime directories exist
for _d in (DATABASE_DIR, LOGS_DIR):
    _d.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------
DB_PATH: Path = DATABASE_DIR / "retail.db"
DB_URL: str = f"sqlite:///{DB_PATH.as_posix()}"

# ---------------------------------------------------------------------------
# Mock / pre-baked dataset paths
# ---------------------------------------------------------------------------
MOCK_SALES_PATH: Path = DATA_DIR / "mock_sales_data.csv"
MOCK_PRODUCTS_PATH: Path = DATA_DIR / "mock_products.csv"
MOCK_STORES_PATH: Path = DATA_DIR / "mock_stores.csv"

# ---------------------------------------------------------------------------
# Quarantine / export paths (written at runtime)
# ---------------------------------------------------------------------------
QUARANTINE_DIR: Path = ROOT_DIR / "quarantine"
QUARANTINE_DIR.mkdir(parents=True, exist_ok=True)

QUARANTINE_ORPHANS_PATH: Path = QUARANTINE_DIR / "orphan_keys.csv"
QUARANTINE_INVALID_DATES_PATH: Path = QUARANTINE_DIR / "invalid_dates.csv"
QUARANTINE_REVENUE_MISMATCH_PATH: Path = QUARANTINE_DIR / "revenue_mismatch.csv"

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
LOG_LEVEL: str = os.environ.get("LOG_LEVEL", "INFO").upper()
LOG_FILE: Path = LOGS_DIR / "pipeline.log"

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(),
    ],
)

# ---------------------------------------------------------------------------
# Schema column contracts
# ---------------------------------------------------------------------------
SALES_REQUIRED_COLS: list[str] = [
    "sale_id",
    "store_id",
    "product_id",
    "quantity",
    "sale_date",
    "amount",
]

PRODUCTS_REQUIRED_COLS: list[str] = [
    "product_id",
    "product_name",
    "category",
    "price",
]

STORES_REQUIRED_COLS: list[str] = [
    "store_id",
    "store_name",
    "city",
    "region",
]

# ---------------------------------------------------------------------------
# Revenue mismatch tolerance (floating-point rounding slack)
# ---------------------------------------------------------------------------
REVENUE_TOLERANCE: float = 0.02  # ±$0.02
