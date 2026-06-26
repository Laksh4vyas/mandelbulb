"""
clean.py — Final data preparation layer before transformation.

Applies cosmetic cleansing steps on top of the validated frame:
  • String normalisation (strip, title-case for categorical columns)
  • Type enforcement (int for quantity, float for amount/price)
  • Derived column generation (year, month, quarter, day_of_week)
  • Category label normalisation
"""

from __future__ import annotations

import logging

import pandas as pd

log = logging.getLogger(__name__)


def clean_sales(df: pd.DataFrame) -> pd.DataFrame:
    """
    Apply final cleaning transformations to the validated sales DataFrame.

    Parameters
    ----------
    df : pd.DataFrame
        Output of validate_and_clean().

    Returns
    -------
    pd.DataFrame
        Cleaned, analytics-ready frame.
    """
    out = df.copy()

    # Ensure correct types
    out["quantity"] = out["quantity"].fillna(0).astype(int)
    out["amount"] = out["amount"].astype(float).round(4)

    # String normalisation
    for col in ("sale_id", "product_id", "store_id"):
        out[col] = out[col].astype(str).str.strip()

    # Temporal feature engineering
    if pd.api.types.is_datetime64_any_dtype(out["sale_date"]):
        out["sale_year"] = out["sale_date"].dt.year
        out["sale_month"] = out["sale_date"].dt.month
        out["sale_quarter"] = out["sale_date"].dt.quarter
        out["sale_day_of_week"] = out["sale_date"].dt.day_name()
        out["sale_week"] = out["sale_date"].dt.isocalendar().week.astype(int)
    else:
        log.warning("sale_date column is not datetime — skipping temporal features.")

    log.info("clean_sales complete — %d rows, %d columns.", len(out), len(out.columns))
    return out


def clean_products(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normalise the product catalog frame.
    Works with or without an optional 'brand' column.
    """
    out = df.copy()
    out["product_id"]   = out["product_id"].astype(str).str.strip()
    out["product_name"] = out["product_name"].astype(str).str.strip()
    out["category"]     = out["category"].astype(str).str.strip().str.title()
    out["price"]        = out["price"].astype(float).round(4)
    if "brand" in out.columns:
        out["brand"] = out["brand"].astype(str).str.strip()
    log.info("clean_products complete — %d products.", len(out))
    return out


def clean_stores(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normalise the store directory frame.
    Works with or without optional 'state' / 'country' columns.
    """
    out = df.copy()
    # Only strip columns that actually exist in this dataset
    for col in ("store_id", "store_name", "city", "state", "region", "country"):
        if col in out.columns:
            out[col] = out[col].astype(str).str.strip()
    if "city" in out.columns:
        out["city"] = out["city"].str.title()
    if "region" in out.columns:
        out["region"] = out["region"].str.title()
    log.info("clean_stores complete — %d stores.", len(out))
    return out