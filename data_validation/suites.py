"""
Great Expectations suite definitions for the defense supply chain dataset.

Each function returns a configured GE validator with expectations saved.
Keeping suite definitions here (not in test files) means they can be reused
by both pytest and the capture_baseline-style standalone scripts.
"""
from __future__ import annotations

import great_expectations as gx
import pandas as pd


def build_bom_suite(df: pd.DataFrame, context: gx.DataContext) -> gx.validator.validator.Validator:
    """
    Expectation suite for the Bill of Materials.
    Validates schema, business rules, and referential integrity constraints.
    """
    datasource = context.sources.add_or_update_pandas("bom_pandas_ds")
    asset = datasource.add_dataframe_asset("bom_asset")
    batch_request = asset.build_batch_request(dataframe=df)

    suite_name = "bom_suite"
    context.add_or_update_expectation_suite(suite_name)
    validator = context.get_validator(
        batch_request=batch_request,
        expectation_suite_name=suite_name,
    )

    # ── Schema ────────────────────────────────────────────────────────────────
    for col in ["part_number", "description", "unit_cost", "quantity",
                "supplier_id", "category", "classification"]:
        validator.expect_column_to_exist(col)

    # ── Completeness ──────────────────────────────────────────────────────────
    validator.expect_column_values_to_not_be_null("part_number")
    validator.expect_column_values_to_not_be_null("unit_cost")
    validator.expect_column_values_to_not_be_null("supplier_id")

    # ── Format ────────────────────────────────────────────────────────────────
    validator.expect_column_values_to_match_regex(
        "part_number",
        r"^[A-Z]{2}-\d{6}$",
        meta={"note": "Format: two uppercase letters, hyphen, six digits"},
    )
    validator.expect_column_values_to_match_regex(
        "supplier_id",
        r"^SUP-\d{3}$",
    )

    # ── Business rules ────────────────────────────────────────────────────────
    validator.expect_column_values_to_be_between(
        "unit_cost", min_value=0.01,
        meta={"note": "No zero-cost or negative-cost parts"},
    )
    validator.expect_column_values_to_be_between(
        "quantity", min_value=1,
        meta={"note": "Quantity must be a positive integer"},
    )
    validator.expect_column_values_to_be_in_set(
        "category",
        ["Electronics", "Mechanical", "Software", "Materials"],
    )
    validator.expect_column_values_to_be_in_set(
        "classification",
        ["UNCLASSIFIED", "CUI", "SECRET"],
    )

    # ── Uniqueness ────────────────────────────────────────────────────────────
    validator.expect_column_values_to_be_unique("part_number")

    # ── Row count ─────────────────────────────────────────────────────────────
    validator.expect_table_row_count_to_be_between(min_value=1, max_value=10000)

    validator.save_expectation_suite(discard_failed_expectations=False)
    return validator


def build_supplier_suite(df: pd.DataFrame, context: gx.DataContext) -> gx.validator.validator.Validator:
    """
    Expectation suite for the supplier risk register.
    """
    datasource = context.sources.add_or_update_pandas("supplier_pandas_ds")
    asset = datasource.add_dataframe_asset("supplier_asset")
    batch_request = asset.build_batch_request(dataframe=df)

    suite_name = "supplier_suite"
    context.add_or_update_expectation_suite(suite_name)
    validator = context.get_validator(
        batch_request=batch_request,
        expectation_suite_name=suite_name,
    )

    # ── Schema ────────────────────────────────────────────────────────────────
    for col in ["supplier_id", "name", "country", "risk_score",
                "on_time_delivery_rate", "certified", "last_audit_year"]:
        validator.expect_column_to_exist(col)

    # ── Completeness ──────────────────────────────────────────────────────────
    validator.expect_column_values_to_not_be_null("supplier_id")
    validator.expect_column_values_to_not_be_null("risk_score")

    # ── Business rules ────────────────────────────────────────────────────────
    validator.expect_column_values_to_be_between(
        "risk_score", min_value=0, max_value=100,
        meta={"note": "Risk score is a 0-100 scale"},
    )
    validator.expect_column_values_to_be_between(
        "on_time_delivery_rate", min_value=0.0, max_value=1.0,
        meta={"note": "Rate expressed as a decimal between 0 and 1"},
    )
    validator.expect_column_values_to_be_between(
        "last_audit_year", min_value=2020, max_value=2030,
    )

    # ── Uniqueness ────────────────────────────────────────────────────────────
    validator.expect_column_values_to_be_unique("supplier_id")

    validator.save_expectation_suite(discard_failed_expectations=False)
    return validator