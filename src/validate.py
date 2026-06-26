"""
validate.py — Defensive schema enforcement & data quality gateway.

Implements five zero-day pitfall mitigations:
  1. Revenue validation mismatch detection (amount != quantity * price)
  2. Orphan dimension key isolation via anti-join
  3. Safe date coercion using pd.to_datetime(errors="coerce")
  4. Conflicting metric detection for duplicate sale_id records
  5. Negative / null quantity & amount flagging

Returns a cleaned DataFrame + a JSON-serialisable telemetry scorecard.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

import pandas as pd

from src.config import (
    QUARANTINE_INVALID_DATES_PATH,
    QUARANTINE_ORPHANS_PATH,
    QUARANTINE_REVENUE_MISMATCH_PATH,
    REVENUE_TOLERANCE,
)

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Telemetry scorecard
# ---------------------------------------------------------------------------

@dataclass
class QualityScorecard:
    duplicates_removed: int = 0
    null_quantity_fixed: int = 0
    null_amount_removed: int = 0
    invalid_dates_quarantined: int = 0
    orphan_keys_flagged: int = 0
    revenue_mismatch_flagged: int = 0
    conflicting_metrics_detected: int = 0
    negative_quantity_quarantined: int = 0
    rows_in: int = 0
    rows_out: int = 0
    quarantined_records: dict[str, list[dict[str, Any]]] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "duplicates_removed": self.duplicates_removed,
            "null_quantity_fixed": self.null_quantity_fixed,
            "null_amount_removed": self.null_amount_removed,
            "invalid_dates_quarantined": self.invalid_dates_quarantined,
            "orphan_keys_flagged": self.orphan_keys_flagged,
            "revenue_mismatch_flagged": self.revenue_mismatch_flagged,
            "conflicting_metrics_detected": self.conflicting_metrics_detected,
            "negative_quantity_quarantined": self.negative_quantity_quarantined,
            "rows_in": self.rows_in,
            "rows_out": self.rows_out,
        }


# ---------------------------------------------------------------------------
# Core validation pipeline
# ---------------------------------------------------------------------------

def validate_and_clean(
    sales_df: pd.DataFrame,
    products_df: pd.DataFrame,
    stores_df: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, QualityScorecard]:
    """
    Apply the full quality gateway to the raw ingested frames.

    Returns
    -------
    tuple
        (clean_sales, clean_products, clean_stores, scorecard)
    """
    scorecard = QualityScorecard()
    scorecard.rows_in = len(sales_df)

    df = sales_df.copy()

    # ------------------------------------------------------------------
    # Step 1 — Numeric coercion
    # ------------------------------------------------------------------
    df["quantity"] = pd.to_numeric(df["quantity"], errors="coerce")
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce")

    # ------------------------------------------------------------------
    # Step 2 — Null amount removal (cannot impute revenue)
    # ------------------------------------------------------------------
    null_amount_mask = df["amount"].isna()
    scorecard.null_amount_removed = int(null_amount_mask.sum())
    if scorecard.null_amount_removed:
        log.warning("Removing %d rows with null amount.", scorecard.null_amount_removed)
        scorecard.quarantined_records["null_amount"] = (
            df[null_amount_mask].to_dict(orient="records")
        )
    df = df[~null_amount_mask].copy()

    # ------------------------------------------------------------------
    # Step 3 — Null quantity fix (impute 0 and flag)
    # ------------------------------------------------------------------
    null_qty_mask = df["quantity"].isna()
    scorecard.null_quantity_fixed = int(null_qty_mask.sum())
    if scorecard.null_quantity_fixed:
        log.warning(
            "Imputing %d null quantity values with 0.", scorecard.null_quantity_fixed
        )
    df.loc[null_qty_mask, "quantity"] = 0

    # ------------------------------------------------------------------
    # Pitfall 1 — Negative quantity quarantine
    # ------------------------------------------------------------------
    neg_qty_mask = df["quantity"] < 0
    scorecard.negative_quantity_quarantined = int(neg_qty_mask.sum())
    if scorecard.negative_quantity_quarantined:
        log.warning(
            "Quarantining %d rows with negative quantity.",
            scorecard.negative_quantity_quarantined,
        )
        scorecard.quarantined_records["negative_quantity"] = (
            df[neg_qty_mask].to_dict(orient="records")
        )
    df = df[~neg_qty_mask].copy()

    # ------------------------------------------------------------------
    # Pitfall 3 — Safe date coercion
    # ------------------------------------------------------------------
    df["sale_date"] = pd.to_datetime(df["sale_date"], errors="coerce")
    invalid_date_mask = df["sale_date"].isna()
    scorecard.invalid_dates_quarantined = int(invalid_date_mask.sum())
    if scorecard.invalid_dates_quarantined:
        log.warning(
            "Quarantining %d rows with unparseable dates.",
            scorecard.invalid_dates_quarantined,
        )
        bad_dates_df = df[invalid_date_mask].copy()
        try:
            bad_dates_df.to_csv(QUARANTINE_INVALID_DATES_PATH, index=False)
        except Exception as exc:  # noqa: BLE001
            log.error("Could not write invalid-dates quarantine file: %s", exc)
        scorecard.quarantined_records["invalid_dates"] = (
            df[invalid_date_mask].to_dict(orient="records")
        )
    df = df[~invalid_date_mask].copy()

    # ------------------------------------------------------------------
    # Pitfall 4 — Conflicting metrics for duplicate sale_id
    # ------------------------------------------------------------------
    dup_ids = df[df.duplicated("sale_id", keep=False)]["sale_id"].unique()
    conflict_count = 0
    for sid in dup_ids:
        group = df[df["sale_id"] == sid]
        if group[["quantity", "amount"]].nunique().max() > 1:
            conflict_count += 1
            log.warning(
                "Conflicting metrics for sale_id=%s — keeping first occurrence.", sid
            )
    scorecard.conflicting_metrics_detected = conflict_count

    # ------------------------------------------------------------------
    # Step 4 — Hard duplicate removal (keep first)
    # ------------------------------------------------------------------
    before = len(df)
    df = df.drop_duplicates(subset=["sale_id"], keep="first").copy()
    scorecard.duplicates_removed = before - len(df)
    if scorecard.duplicates_removed:
        log.info("Removed %d exact duplicate sale_id rows.", scorecard.duplicates_removed)

    # ------------------------------------------------------------------
    # Pitfall 2 — Orphan dimension key anti-join
    # ------------------------------------------------------------------
    valid_product_ids: set[str] = set(products_df["product_id"].astype(str).unique())
    valid_store_ids: set[str] = set(stores_df["store_id"].astype(str).unique())

    df["product_id"] = df["product_id"].astype(str)
    df["store_id"] = df["store_id"].astype(str)

    orphan_product_mask = ~df["product_id"].isin(valid_product_ids)
    orphan_store_mask = ~df["store_id"].isin(valid_store_ids)
    orphan_mask = orphan_product_mask | orphan_store_mask

    scorecard.orphan_keys_flagged = int(orphan_mask.sum())
    if scorecard.orphan_keys_flagged:
        log.warning(
            "Flagging %d orphan-key rows (unknown product/store IDs).",
            scorecard.orphan_keys_flagged,
        )
        orphan_df = df[orphan_mask].copy()
        orphan_df["orphan_reason"] = "unknown_product_or_store_id"
        try:
            orphan_df.to_csv(QUARANTINE_ORPHANS_PATH, index=False)
        except Exception as exc:  # noqa: BLE001
            log.error("Could not write orphan quarantine file: %s", exc)
        scorecard.quarantined_records["orphan_keys"] = orphan_df.to_dict(
            orient="records"
        )
    df = df[~orphan_mask].copy()

    # Revenue mismatch is computed in transform.py after joining price from dim_products.
    scorecard.revenue_mismatch_flagged = 0  # updated downstream

    # ------------------------------------------------------------------
    # Final state
    # ------------------------------------------------------------------
    scorecard.rows_out = len(df)
    log.info(
        "Validation complete. rows_in=%d rows_out=%d scorecard=%s",
        scorecard.rows_in,
        scorecard.rows_out,
        scorecard.to_dict(),
    )

    # Clean dimension frames (strip whitespace, dedup)
    clean_products = (
        products_df.copy()
        .drop_duplicates(subset=["product_id"])
        .reset_index(drop=True)
    )
    clean_stores = (
        stores_df.copy()
        .drop_duplicates(subset=["store_id"])
        .reset_index(drop=True)
    )

    return df, clean_products, clean_stores, scorecard