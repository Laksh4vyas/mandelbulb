"""
extract.py — Dual-mode ingestion engine.

Accepts data from either:
  • Local file paths  (str | Path) — used by the CLI pipeline runner
  • Streamlit UploadedFile buffers — used by the Streamlit UI

Returns validated raw DataFrames ready for the quality gateway.
"""

from __future__ import annotations

import logging
from io import BytesIO, StringIO
from pathlib import Path
from typing import Union

import pandas as pd

from src.config import (
    MOCK_PRODUCTS_PATH,
    MOCK_SALES_PATH,
    MOCK_STORES_PATH,
    PRODUCTS_REQUIRED_COLS,
    SALES_REQUIRED_COLS,
    STORES_REQUIRED_COLS,
)

log = logging.getLogger(__name__)

# Type alias for the supported file input modes
FileInput = Union[str, Path, BytesIO, StringIO]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _read_csv(source: FileInput, required_cols: list[str], label: str) -> pd.DataFrame:
    """
    Read a CSV from a file path or a file-like buffer.

    Raises
    ------
    ValueError
        When required columns are absent from the loaded frame.
    """
    try:
        if isinstance(source, (str, Path)):
            df = pd.read_csv(source, encoding="utf-8", low_memory=False)
            log.info("Loaded %s from path: %s (%d rows)", label, source, len(df))
        else:
            # Streamlit UploadedFile exposes a file-like interface; reset the
            # read cursor so repeated calls inside a session don't return empty.
            if hasattr(source, "seek"):
                source.seek(0)
            df = pd.read_csv(source, encoding="utf-8", low_memory=False)
            log.info("Loaded %s from upload buffer (%d rows)", label, len(df))
    except Exception as exc:  # noqa: BLE001
        log.error("Failed to read %s: %s", label, exc)
        raise

    missing = set(required_cols) - set(df.columns.tolist())
    if missing:
        log.warning(
            "[%s] Optional/expected columns absent: %s — proceeding without them. "
            "Found columns: %s",
            label, missing, list(df.columns)
        )

    # Normalise column names: strip leading/trailing whitespace
    df.columns = [c.strip() for c in df.columns]
    return df


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def extract_sales(source: FileInput | None = None) -> pd.DataFrame:
    """
    Ingest sales data.

    Parameters
    ----------
    source:
        File path / buffer.  Falls back to the built-in mock dataset when *None*.
    """
    effective_source = source if source is not None else MOCK_SALES_PATH
    return _read_csv(effective_source, SALES_REQUIRED_COLS, "sales")


def extract_products(source: FileInput | None = None) -> pd.DataFrame:
    """
    Ingest product catalog.

    Parameters
    ----------
    source:
        File path / buffer.  Falls back to the built-in mock dataset when *None*.
    """
    effective_source = source if source is not None else MOCK_PRODUCTS_PATH
    return _read_csv(effective_source, PRODUCTS_REQUIRED_COLS, "products")


def extract_stores(source: FileInput | None = None) -> pd.DataFrame:
    """
    Ingest store directory.

    Parameters
    ----------
    source:
        File path / buffer.  Falls back to the built-in mock dataset when *None*.
    """
    effective_source = source if source is not None else MOCK_STORES_PATH
    return _read_csv(effective_source, STORES_REQUIRED_COLS, "stores")


def extract_all(
    sales_source: FileInput | None = None,
    products_source: FileInput | None = None,
    stores_source: FileInput | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Convenience wrapper: extract all three datasets in one call.

    Returns
    -------
    tuple[DataFrame, DataFrame, DataFrame]
        (sales_df, products_df, stores_df)
    """
    sales_df = extract_sales(sales_source)
    products_df = extract_products(products_source)
    stores_df = extract_stores(stores_source)
    return sales_df, products_df, stores_df