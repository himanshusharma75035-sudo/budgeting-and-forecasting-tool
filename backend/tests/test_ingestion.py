"""Tests for the data ingestion domain (DESIGN.md 5.4).

Fixtures here were adversarially verified; the expected values are intentionally exact.
"""

from __future__ import annotations

from decimal import Decimal

import pandas as pd
import pytest

from app.domain.ingestion import (
    LongRecord,
    detect_layout,
    parse_amount,
    pivot_wide_to_long,
    validate_wide,
)

# --- parse_amount -----------------------------------------------------------------


def test_parse_amount_plain_decimal() -> None:
    assert parse_amount("1234.50") == Decimal("1234.50")


def test_parse_amount_negative() -> None:
    assert parse_amount("-5") == Decimal("-5")


@pytest.mark.parametrize("blank", ["", None, "   "])
def test_parse_amount_blank_is_none(blank: object) -> None:
    assert parse_amount(blank) is None


def test_parse_amount_accepts_numeric_types() -> None:
    assert parse_amount(5) == Decimal("5")
    assert parse_amount(2.5) == Decimal("2.5")


@pytest.mark.parametrize("bad", ["1,234", "$5", "5%", "(5)", "1 234", "1.2.3"])
def test_parse_amount_rejects_dirty_values(bad: str) -> None:
    with pytest.raises(ValueError):
        parse_amount(bad)


# --- detect_layout ----------------------------------------------------------------


def test_detect_layout_wide() -> None:
    df = pd.DataFrame({"account_code": ["4000"], "2026-01": ["10"]})
    assert detect_layout(df) == "WIDE"


def test_detect_layout_long() -> None:
    df = pd.DataFrame(
        {"account_code": ["4000"], "period": ["2026-01"], "amount": ["10"]}
    )
    assert detect_layout(df) == "LONG"


# --- pivot_wide_to_long -----------------------------------------------------------


def test_pivot_wide_to_long_skips_blank_cell() -> None:
    df = pd.DataFrame(
        [
            {
                "account_code": "4000",
                "entity_code": "HQ",
                "department_code": "SALES",
                "project_code": "NONE",
                "region_code": "NA",
                "currency": "USD",
                "2026-01": "1500.25",
                "2026-02": "",  # blank -> NULL, skipped
            }
        ]
    )
    records = pivot_wide_to_long(df)
    assert records == [
        LongRecord(
            account_code="4000",
            entity_code="HQ",
            department_code="SALES",
            project_code="NONE",
            region_code="NA",
            period_key=202601,
            amount=Decimal("1500.25"),
            currency="USD",
        )
    ]
    assert len(records) == 1
    assert records[0].period_key == 202601
    assert records[0].amount == Decimal("1500.25")


def test_pivot_wide_to_long_fills_dim_defaults() -> None:
    df = pd.DataFrame([{"account_code": "4000", "2026-01": "10"}])
    (record,) = pivot_wide_to_long(df)
    assert record.entity_code == "ALL"
    assert record.department_code == "UNALLOC"
    assert record.project_code == "NONE"
    assert record.region_code == "ALL"
    assert record.currency == "USD"


# --- validate_wide ----------------------------------------------------------------


def test_validate_wide_flags_unknown_account_bad_period_and_duplicates() -> None:
    df = pd.DataFrame(
        [
            # ok row
            {"account_code": "4000", "entity_code": "HQ", "2026-01": "100"},
            # unknown account -> RowError
            {"account_code": "9999", "entity_code": "HQ", "2026-01": "200"},
            # bad numeric value -> RowError
            {"account_code": "4000", "entity_code": "BR", "2026-01": "1,234"},
            # duplicate natural key of row 1 -> RowError
            {"account_code": "4000", "entity_code": "HQ", "2026-01": "300"},
        ]
    )
    report = validate_wide(
        df,
        known_account_codes={"4000"},
        known_dim_codes={"entity_code": {"HQ", "BR"}},
    )
    assert report.layout == "WIDE"
    assert report.rows_total == 4
    fields = sorted(e.field for e in report.errors)
    rows = sorted(e.row for e in report.errors)
    # one unknown account (row 2), one bad amount (row 3), one duplicate (row 4)
    assert fields == ["2026-01", "2026-01", "account_code"]
    assert rows == [2, 3, 4]
    assert len(report.errors) == 3
    assert report.rows_ok == 1
    assert report.ok is False


def test_validate_wide_unknown_dimension_code() -> None:
    df = pd.DataFrame(
        [{"account_code": "4000", "entity_code": "ZZ", "2026-01": "100"}]
    )
    report = validate_wide(
        df,
        known_account_codes={"4000"},
        known_dim_codes={"entity_code": {"HQ"}},
    )
    assert len(report.errors) == 1
    assert report.errors[0].field == "entity_code"
    assert report.rows_ok == 0
