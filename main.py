"""
main.py — Top-level ETL orchestration runner.

Provides a single `run_pipeline()` function that chains:
  extract → validate → clean → transform → load

Callable from the CLI or imported by the Streamlit app.

Usage
-----
    python main.py                         # Demo mode (mock data)
    python main.py --sales path/to/s.csv   # Custom file mode
"""

from __future__ import annotations

import argparse
import logging
import time
from pathlib import Path
from typing import Any, Optional

import pandas as pd

from src.clean import clean_products, clean_sales, clean_stores
from src.extract import extract_all
from src.load import load_warehouse
from src.transform import transform_all
from src.validate import QualityScorecard, validate_and_clean

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Pipeline result payload
# ---------------------------------------------------------------------------

class PipelineResult:
    """Structured container returned by run_pipeline()."""

    def __init__(
        self,
        fact_sales: pd.DataFrame,
        dim_products: pd.DataFrame,
        dim_stores: pd.DataFrame,
        scorecard: QualityScorecard,
        elapsed_seconds: float,
        log_entries: list[str],
    ) -> None:
        self.fact_sales = fact_sales
        self.dim_products = dim_products
        self.dim_stores = dim_stores
        self.scorecard = scorecard
        self.elapsed_seconds = elapsed_seconds
        self.log_entries = log_entries


# ---------------------------------------------------------------------------
# Master orchestrator
# ---------------------------------------------------------------------------

def run_pipeline(
    source_type: str = "demo",
    data_inputs: Optional[dict[str, Any]] = None,
) -> PipelineResult:
    """
    Execute the full ETL pipeline.

    Parameters
    ----------
    source_type : str
        "demo"   — use the built-in pre-baked mock CSVs.
        "upload" — use file-like buffers from data_inputs.
    data_inputs : dict, optional
        When source_type=="upload", expects keys:
            "sales"    -> file path or buffer
            "products" -> file path or buffer
            "stores"   -> file path or buffer

    Returns
    -------
    PipelineResult
    """
    t0 = time.perf_counter()
    log_entries: list[str] = []

    def _log(msg: str) -> None:
        log.info(msg)
        log_entries.append(msg)

    _log(f"🚀 Pipeline started — source_type='{source_type}'")

    # ------------------------------------------------------------------
    # EXTRACT
    # ------------------------------------------------------------------
    if source_type == "demo" or data_inputs is None:
        sales_src = products_src = stores_src = None
    else:
        sales_src = data_inputs.get("sales")
        products_src = data_inputs.get("products")
        stores_src = data_inputs.get("stores")

    raw_sales, raw_products, raw_stores = extract_all(sales_src, products_src, stores_src)
    _log(f"✅ Sales Dataset Loaded ({len(raw_sales)} rows ingested)")
    _log(f"✅ Product Catalog Ingested ({len(raw_products)} rows mapped)")
    _log(f"✅ Store Dimensions Loaded ({len(raw_stores)} locations mapped)")

    # ------------------------------------------------------------------
    # VALIDATE
    # ------------------------------------------------------------------
    validated_sales, validated_products, validated_stores, scorecard = validate_and_clean(
        raw_sales, raw_products, raw_stores
    )
    _log(
        f"✅ Data Quality Matrix Applied "
        f"(Duplicates Pruned: {scorecard.duplicates_removed} | "
        f"Nulls Coerced: {scorecard.null_quantity_fixed} | "
        f"Orphans Flagged: {scorecard.orphan_keys_flagged} | "
        f"Revenue Mismatches: {scorecard.revenue_mismatch_flagged})"
    )

    # ------------------------------------------------------------------
    # CLEAN
    # ------------------------------------------------------------------
    clean_s = clean_sales(validated_sales)
    clean_p = clean_products(validated_products)
    clean_st = clean_stores(validated_stores)

    # ------------------------------------------------------------------
    # TRANSFORM
    # ------------------------------------------------------------------
    fact_sales, dim_products, dim_stores, mismatch_count = transform_all(clean_s, clean_p, clean_st)
    scorecard.revenue_mismatch_flagged = mismatch_count

    # ------------------------------------------------------------------
    # LOAD
    # ------------------------------------------------------------------
    load_warehouse(fact_sales, dim_products, dim_stores)
    _log("✅ Analytical Target Warehouse Layer Synchronized (SQLite Sync Completed)")

    elapsed = time.perf_counter() - t0
    _log(f"🚀 Pipeline execution loop terminated successfully in {elapsed:.4f} seconds.")

    return PipelineResult(
        fact_sales=fact_sales,
        dim_products=dim_products,
        dim_stores=dim_stores,
        scorecard=scorecard,
        elapsed_seconds=elapsed,
        log_entries=log_entries,
    )


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Retail Data Engineering & Analytics Platform — CLI Runner"
    )
    parser.add_argument("--sales", type=Path, default=None, help="Path to sales CSV")
    parser.add_argument("--products", type=Path, default=None, help="Path to products CSV")
    parser.add_argument("--stores", type=Path, default=None, help="Path to stores CSV")
    args = parser.parse_args()

    if any([args.sales, args.products, args.stores]):
        inputs = {"sales": args.sales, "products": args.products, "stores": args.stores}
        result = run_pipeline(source_type="upload", data_inputs=inputs)
    else:
        result = run_pipeline(source_type="demo")

    print("\n--- Pipeline Execution Log ---")
    for entry in result.log_entries:
        print(entry)

    print("\n--- Quality Scorecard ---")
    for k, v in result.scorecard.to_dict().items():
        print(f"  {k}: {v}")

    print(f"\nfact_sales shape  : {result.fact_sales.shape}")
    print(f"dim_products shape: {result.dim_products.shape}")
    print(f"dim_stores shape  : {result.dim_stores.shape}")