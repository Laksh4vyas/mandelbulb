"""
report.py — Aggregated report generation & multi-format export engine.

Generates:
  • Cleaned analytical sales base (.csv)
  • Aggregated revenue performance report (.csv)
  • Raw bytes of the SQLite database (.db) for download
"""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

from src.config import DATABASE_DIR, DB_PATH
from src.transform import (
    aggregate_product_performance,
    aggregate_revenue_by_month,
    aggregate_store_performance,
)

log = logging.getLogger(__name__)

REPORTS_DIR: Path = DATABASE_DIR.parent / "reports"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# CSV report writers
# ---------------------------------------------------------------------------

def generate_cleaned_sales_csv(fact_sales: pd.DataFrame) -> bytes:
    """Return cleaned fact_sales as UTF-8 CSV bytes for download."""
    return fact_sales.to_csv(index=False).encode("utf-8")


def generate_revenue_report_csv(
    fact_sales: pd.DataFrame,
    dim_products: pd.DataFrame,
    dim_stores: pd.DataFrame,
) -> bytes:
    """
    Generate an aggregated revenue report (monthly × region × category)
    and return as UTF-8 CSV bytes.
    """
    monthly = aggregate_revenue_by_month(fact_sales, dim_stores, dim_products)
    product_perf = aggregate_product_performance(fact_sales, dim_products)
    store_perf = aggregate_store_performance(fact_sales, dim_stores)

    # Persist to disk as well
    monthly.to_csv(REPORTS_DIR / "revenue_by_month.csv", index=False)
    product_perf.to_csv(REPORTS_DIR / "product_performance.csv", index=False)
    store_perf.to_csv(REPORTS_DIR / "store_performance.csv", index=False)

    log.info("Revenue reports written to %s", REPORTS_DIR)
    return monthly.to_csv(index=False).encode("utf-8")


def get_db_bytes() -> bytes:
    """Read the SQLite .db file and return raw bytes for binary download."""
    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"SQLite database not found at {DB_PATH}. "
            "Run the pipeline at least once before downloading."
        )
    return DB_PATH.read_bytes()