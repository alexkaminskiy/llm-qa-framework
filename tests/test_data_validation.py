from __future__ import annotations

import sqlite3
from pathlib import Path

import great_expectations as gx
import pandas as pd
import pytest

from data_validation.setup_db import setup_supply_chain_db, DB_PATH
from data_validation.suites import build_bom_suite, build_supplier_suite

DATA_DIR = Path(__file__).parent.parent / "data"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def bom_df() -> pd.DataFrame:
    return pd.read_csv(DATA_DIR / "bom.csv")


@pytest.fixture(scope="module")
def suppliers_df() -> pd.DataFrame:
    return pd.read_csv(DATA_DIR / "suppliers.csv")


@pytest.fixture(scope="module")
def db_path() -> Path:
    """Creates SQLite DB from CSVs, returns path. sqlite3 is DBAPI2-compliant
    unlike SQLAlchemy 2.x connections — pandas requires .cursor() to exist."""
    return setup_supply_chain_db()


@pytest.fixture(scope="module")
def gx_context() -> gx.DataContext:
    return gx.get_context(mode="ephemeral")


@pytest.fixture(scope="module")
def db_connection(db_path):
    """Provides a DB connection for SQL-based tests. Remember to close it."""
    conn = sqlite3.connect(str(db_path))
    yield conn
    conn.close()


# ---------------------------------------------------------------------------
# Layer 1: CSV / pandas validation
# ---------------------------------------------------------------------------

def test_bom_schema_and_business_rules(bom_df, gx_context) -> None:
    validator = build_bom_suite(bom_df, gx_context)
    checkpoint = gx_context.add_or_update_checkpoint(
        name="bom_checkpoint",
        validator=validator,
    )
    result = checkpoint.run()
    assert result.success, f"BOM validation failed.\n{_format_failures(result)}"


def test_supplier_schema_and_business_rules(suppliers_df, gx_context) -> None:
    validator = build_supplier_suite(suppliers_df, gx_context)
    checkpoint = gx_context.add_or_update_checkpoint(
        name="supplier_checkpoint",
        validator=validator,
    )
    result = checkpoint.run()
    assert result.success, f"Supplier validation failed.\n{_format_failures(result)}"


# ---------------------------------------------------------------------------
# Layer 2: SQL validation
# ---------------------------------------------------------------------------

def test_bom_supplier_referential_integrity(db_path, db_connection) -> None:
    query = """
        SELECT b.part_number, b.supplier_id
        FROM bom b
        LEFT JOIN suppliers s ON b.supplier_id = s.supplier_id
        WHERE s.supplier_id IS NULL
    """
    orphaned = pd.read_sql(query, db_connection)

    # with sqlite3.connect(str(db_path)) as conn:
    #     orphaned = pd.read_sql(query, conn)

    assert len(orphaned) == 0, (
        f"Referential integrity violation: {len(orphaned)} BOM records "
        f"reference non-existent suppliers:\n{orphaned.to_string()}"
    )


def test_high_risk_suppliers_not_sole_sourced(db_path, db_connection) -> None:
    query = """
        SELECT
            b.category,
            COUNT(DISTINCT b.supplier_id) AS supplier_count,
            MAX(s.risk_score)             AS max_risk_score
        FROM bom b
        JOIN suppliers s ON b.supplier_id = s.supplier_id
        GROUP BY b.category
        HAVING supplier_count = 1 AND max_risk_score > 50
    """


    # with sqlite3.connect(str(db_path)) as conn:
    #     violations = pd.read_sql(query, conn)
    violations = pd.read_sql(query, db_connection)

    assert len(violations) == 0, (
        f"Supply chain policy violation: categories sole-sourced "
        f"from high-risk suppliers:\n{violations.to_string()}"
    )


def test_total_bom_value_within_expected_range(db_path, db_connection) -> None:
    query = """
        SELECT SUM(unit_cost * quantity) AS total_bom_value
        FROM bom
    """
    # with sqlite3.connect(str(db_path)) as conn:
    #     result = pd.read_sql(query, conn)
    result = pd.read_sql(query, db_connection)

    total = result["total_bom_value"].iloc[0]
    assert 100_000 <= total <= 100_000_000, (
        f"Total BOM value ${total:,.2f} outside expected range. "
        f"Possible data corruption."
    )


def test_all_suppliers_have_recent_audit(db_path, db_connection) -> None:
    query = """
        SELECT supplier_id, name, last_audit_year
        FROM suppliers
        WHERE last_audit_year < 2023
    """
    # with sqlite3.connect(str(db_path)) as conn:
    #     stale = pd.read_sql(query, conn)
    stale = pd.read_sql(query, db_connection)
    assert len(stale) == 0, (
        f"{len(stale)} suppliers have audits older than 2023:\n"
        f"{stale.to_string()}"
    )


# ---------------------------------------------------------------------------
# Layer 3: Cross-dataset consistency
# ---------------------------------------------------------------------------

def test_no_secret_parts_from_non_us_suppliers(bom_df, suppliers_df) -> None:
    merged = bom_df.merge(suppliers_df, on="supplier_id", how="left")
    violations = merged[
        (merged["classification"] == "SECRET") &
        (merged["country"] != "US")
    ]
    assert len(violations) == 0, (
        f"ITAR violation: SECRET parts sourced from non-US suppliers:\n"
        f"{violations[['part_number', 'supplier_id', 'country', 'classification']].to_string()}"
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _format_failures(result) -> str:
    failures = []
    for run_result in result.run_results.values():
        for er in run_result["validation_result"].results:
            if not er.success:
                failures.append(
                    f"  - {er.expectation_config.expectation_type}: "
                    f"{er.expectation_config.kwargs}"
                )
    return "\n".join(failures) if failures else "  (no detail available)"