"""
transform.py — Star Schema construction.

Deconstructs the cleaned flat frame into optimised analytical layers:
  • fact_sales    — numeric measurements + foreign keys + total_revenue
  • dim_products  — product attribute dimension  (price lives here)
  • dim_stores    — store / geography dimension

Revenue mismatch (Pitfall 1) is computed here after joining price from
dim_products, since price is no longer carried in the sales CSV.
"""

from __future__ import annotations

import logging

import pandas as pd

from src.config import QUARANTINE_REVENUE_MISMATCH_PATH, REVENUE_TOLERANCE

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Dimension builders
# ---------------------------------------------------------------------------

def build_dim_products(products_df: pd.DataFrame) -> pd.DataFrame:
    """Build the product dimension table — product_id, product_name, category, price."""
    available_cols = [c for c in ["product_id", "product_name", "category", "price", "brand"]
                      if c in products_df.columns]
    dim = products_df[available_cols].drop_duplicates(subset=["product_id"]).reset_index(drop=True)
    log.info("dim_products built — %d rows.", len(dim))
    return dim


def build_dim_stores(stores_df: pd.DataFrame) -> pd.DataFrame:
    """Build the store dimension table — store_id, store_name, city, region."""
    available_cols = [c for c in ["store_id", "store_name", "city", "state", "region", "country"]
                      if c in stores_df.columns]
    dim = stores_df[available_cols].drop_duplicates(subset=["store_id"]).reset_index(drop=True)
    log.info("dim_stores built — %d rows.", len(dim))
    return dim


# ---------------------------------------------------------------------------
# Fact table builder
# ---------------------------------------------------------------------------

def build_fact_sales(
    sales_df: pd.DataFrame,
    dim_products: pd.DataFrame,
    dim_stores: pd.DataFrame,
) -> pd.DataFrame:
    """
    Build the central fact table.

    After filtering for valid dimension keys, joins price from dim_products
    to compute total_revenue (qty × price) and flag revenue mismatches.

    Columns (post-build):
        sale_id, store_id, product_id, sale_date, temporal features,
        quantity, amount, price, total_revenue, revenue_validation_mismatch
    """
    base_cols = [
        "sale_id", "store_id", "product_id", "sale_date",
        "sale_year", "sale_month", "sale_quarter",
        "sale_day_of_week", "sale_week",
        "quantity", "amount",
    ]
    available = [c for c in base_cols if c in sales_df.columns]
    fact = sales_df[available].copy()

    # Confirm dimension coherence (inner-join semantics)
    valid_product_ids = set(dim_products["product_id"].astype(str))
    valid_store_ids = set(dim_stores["store_id"].astype(str))
    pre = len(fact)
    fact = fact[
        fact["product_id"].astype(str).isin(valid_product_ids)
        & fact["store_id"].astype(str).isin(valid_store_ids)
    ].copy()
    if len(fact) < pre:
        log.warning("Inner-join dropped %d orphan rows.", pre - len(fact))

    # Join price from dim_products to compute total_revenue
    price_lookup = dim_products[["product_id", "price"]].copy()
    fact = fact.merge(price_lookup, on="product_id", how="left")
    fact["total_revenue"] = fact["quantity"] * fact["price"]

    # Pitfall 1 — Revenue validation mismatch
    fact["revenue_validation_mismatch"] = (
        (fact["amount"] - fact["total_revenue"]).abs() > REVENUE_TOLERANCE
    )
    mismatch_count = int(fact["revenue_validation_mismatch"].sum())
    if mismatch_count:
        log.warning("%d rows flagged for revenue mismatch.", mismatch_count)
        try:
            fact[fact["revenue_validation_mismatch"]].to_csv(
                QUARANTINE_REVENUE_MISMATCH_PATH, index=False
            )
        except Exception as exc:  # noqa: BLE001
            log.error("Could not write revenue-mismatch quarantine: %s", exc)

    fact = fact.reset_index(drop=True)
    log.info("fact_sales built — %d rows.", len(fact))
    return fact, mismatch_count


# ---------------------------------------------------------------------------
# Aggregation helpers
# ---------------------------------------------------------------------------

def aggregate_revenue_by_month(
    fact: pd.DataFrame, dim_stores: pd.DataFrame, dim_products: pd.DataFrame
) -> pd.DataFrame:
    """Monthly revenue pivot enriched with store and product metadata."""
    store_cols = [c for c in ["store_id", "store_name", "city", "region"] if c in dim_stores.columns]
    enriched = (
        fact
        .merge(dim_products[["product_id", "product_name", "category"]], on="product_id", how="left")
        .merge(dim_stores[store_cols], on="store_id", how="left")
    )
    group_cols = [c for c in ["sale_year", "sale_month", "region", "category"] if c in enriched.columns]
    monthly = (
        enriched.groupby(group_cols)
        .agg(total_revenue=("amount", "sum"), transaction_count=("sale_id", "count"),
             avg_order_value=("amount", "mean"))
        .reset_index()
    )
    if "sale_year" in monthly.columns and "sale_month" in monthly.columns:
        monthly["year_month"] = (
            monthly["sale_year"].astype(str) + "-"
            + monthly["sale_month"].astype(str).str.zfill(2)
        )
    return monthly


def aggregate_product_performance(
    fact: pd.DataFrame, dim_products: pd.DataFrame
) -> pd.DataFrame:
    """Product-level revenue and volume summary."""
    dim_cols_to_drop = [c for c in dim_products.columns if c != "product_id" and c in fact.columns]
    clean_fact = fact.drop(columns=dim_cols_to_drop)
    merged = clean_fact.merge(dim_products, on="product_id", how="left")
    group_cols = [c for c in ["product_id", "product_name", "category", "brand"] if c in merged.columns]
    agg_dict: dict = {"total_revenue": ("amount", "sum"), "units_sold": ("quantity", "sum"),
                      "transaction_count": ("sale_id", "count")}
    if "price" in merged.columns:
        agg_dict["avg_price"] = ("price", "mean")
    return (
        merged.groupby(group_cols).agg(**agg_dict)
        .reset_index().sort_values("total_revenue", ascending=False).reset_index(drop=True)
    )


def aggregate_store_performance(
    fact: pd.DataFrame, dim_stores: pd.DataFrame
) -> pd.DataFrame:
    """Store-level revenue and volume summary."""
    dim_cols_to_drop = [c for c in dim_stores.columns if c != "store_id" and c in fact.columns]
    clean_fact = fact.drop(columns=dim_cols_to_drop)
    merged = clean_fact.merge(dim_stores, on="store_id", how="left")
    group_cols = [c for c in ["store_id", "store_name", "city", "state", "region"] if c in merged.columns]
    return (
        merged.groupby(group_cols)
        .agg(total_revenue=("amount", "sum"), units_sold=("quantity", "sum"),
             transaction_count=("sale_id", "count"))
        .reset_index().sort_values("total_revenue", ascending=False).reset_index(drop=True)
    )


# ---------------------------------------------------------------------------
# Top-level orchestrator
# ---------------------------------------------------------------------------

def transform_all(
    clean_sales: pd.DataFrame,
    clean_products: pd.DataFrame,
    clean_stores: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, int]:
    """
    Run the full transformation sequence.

    Returns
    -------
    tuple
        (fact_sales, dim_products, dim_stores, revenue_mismatch_count)
    """
    dim_products = build_dim_products(clean_products)
    dim_stores = build_dim_stores(clean_stores)
    fact_sales, mismatch_count = build_fact_sales(clean_sales, dim_products, dim_stores)
    return fact_sales, dim_products, dim_stores, mismatch_count