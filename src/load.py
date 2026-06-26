"""
load.py — Analytical warehouse persistence layer.

Persists Star Schema tables into the local SQLite instance using
SQLAlchemy context managers with strict error isolation.

All write operations use `if_exists="replace"` for idempotent pipeline
re-runs, ensuring the warehouse is always consistent with the latest ETL
pass without requiring manual truncation.
"""

from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import Generator

import pandas as pd
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine

from src.config import DB_URL

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Engine factory (cached per module import)
# ---------------------------------------------------------------------------

def get_engine() -> Engine:
    """
    Create a SQLAlchemy engine bound to the configured SQLite database.

    Returns a new engine on each call so that the module remains stateless
    and safe for multi-threaded Streamlit reruns.
    """
    return create_engine(DB_URL, connect_args={"check_same_thread": False})


@contextmanager
def managed_engine() -> Generator[Engine, None, None]:
    """Context manager that yields an engine and disposes it on exit."""
    engine = get_engine()
    try:
        yield engine
    finally:
        engine.dispose()


# ---------------------------------------------------------------------------
# Table writers
# ---------------------------------------------------------------------------

def _write_table(df: pd.DataFrame, table_name: str, engine: Engine) -> None:
    """Write a DataFrame to an SQLite table with replace semantics."""
    df.to_sql(table_name, con=engine, if_exists="replace", index=False)
    log.info("Persisted table '%s' — %d rows written.", table_name, len(df))


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def load_warehouse(
    fact_sales: pd.DataFrame,
    dim_products: pd.DataFrame,
    dim_stores: pd.DataFrame,
) -> None:
    """
    Load all three Star Schema tables into SQLite.

    Parameters
    ----------
    fact_sales : pd.DataFrame
    dim_products : pd.DataFrame
    dim_stores : pd.DataFrame
    """
    with managed_engine() as engine:
        _write_table(dim_products, "dim_products", engine)
        _write_table(dim_stores, "dim_stores", engine)
        _write_table(fact_sales, "fact_sales", engine)
    log.info("Warehouse load complete — SQLite synchronised at: %s", DB_URL)


def drop_and_reinitialise() -> None:
    """
    Drop all warehouse tables and re-create them as empty shells.

    Used by the Streamlit [Reset Platform] action to ensure the session
    returns to a known clean state.
    """
    with managed_engine() as engine:
        with engine.begin() as conn:
            for table in ("fact_sales", "dim_products", "dim_stores"):
                conn.execute(text(f"DROP TABLE IF EXISTS [{table}]"))
                log.info("Dropped table '%s'.", table)
    log.info("Warehouse re-initialised.")


def get_table_names() -> list[str]:
    """Return the list of tables currently present in the warehouse."""
    with managed_engine() as engine:
        inspector = inspect(engine)
        return inspector.get_table_names()


def query_table(sql: str) -> pd.DataFrame:
    """
    Execute a read-only SQL query against the warehouse and return a DataFrame.

    Parameters
    ----------
    sql : str
        A SELECT statement. Non-SELECT statements are rejected.

    Raises
    ------
    ValueError
        If the query is not a SELECT statement.
    """
    normalised = sql.strip().upper()
    if not normalised.startswith("SELECT"):
        raise ValueError("Only SELECT queries are permitted in the Query Studio.")

    with managed_engine() as engine:
        return pd.read_sql(text(sql), con=engine)