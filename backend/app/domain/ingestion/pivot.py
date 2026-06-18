"""Wide->long pivot and long-frame normalization (DESIGN.md 5.4).

The DB is LONG/tidy -- one fact row per ``account x period x dimension-combo``. The Excel
template is WIDE. This module bridges the two: it melts the ``YYYY-MM`` period columns of a
WIDE frame into one :class:`LongRecord` per non-blank cell, and normalizes an already-LONG
frame the same way. Blank cells are skipped (NULL, not zero) and absent dimension codes are
filled with the canonical defaults from DESIGN.md 5.4.

These functions assume the frame has already passed :mod:`app.domain.ingestion.validator`;
they coerce rather than re-validate. ``period_key`` is the smart-integer ``YYYYMM``.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

import pandas as pd

from app.domain.ingestion.parser import period_columns
from app.domain.ingestion.validator import parse_amount
from app.domain.periods import parse_period

# Canonical dimension defaults when a code is absent/blank (DESIGN.md 5.4).
_DIM_DEFAULTS = {
    "entity_code": "ALL",
    "department_code": "UNALLOC",
    "project_code": "NONE",
    "region_code": "ALL",
}


@dataclass(frozen=True)
class LongRecord:
    """One tidy fact row, ready for UPSERT into the LONG ``entries`` table."""

    account_code: str
    entity_code: str
    department_code: str
    project_code: str
    region_code: str
    period_key: int
    amount: Decimal
    currency: str


def _str_cell(row: pd.Series, column: str) -> str:
    """Stripped string for ``column``; empty string for missing/NaN/None."""
    if column not in row.index:
        return ""
    value = row[column]
    if value is None:
        return ""
    if isinstance(value, float) and value != value:  # NaN
        return ""
    return str(value).strip()


def _dim(row: pd.Series, column: str) -> str:
    """Dimension code, falling back to the canonical default when blank."""
    return _str_cell(row, column) or _DIM_DEFAULTS[column]


def _currency(row: pd.Series, default_currency: str) -> str:
    return _str_cell(row, "currency") or default_currency


def pivot_wide_to_long(df: pd.DataFrame, *, default_currency: str = "USD") -> list[LongRecord]:
    """Melt a WIDE frame's period columns into one :class:`LongRecord` per non-blank cell."""
    periods = period_columns(df)
    records: list[LongRecord] = []
    for _, row in df.iterrows():
        account = _str_cell(row, "account_code")
        entity = _dim(row, "entity_code")
        department = _dim(row, "department_code")
        project = _dim(row, "project_code")
        region = _dim(row, "region_code")
        currency = _currency(row, default_currency)
        for col in periods:
            amount = parse_amount(_str_cell(row, col))
            if amount is None:  # blank cell -> NULL, skipped
                continue
            records.append(
                LongRecord(
                    account_code=account,
                    entity_code=entity,
                    department_code=department,
                    project_code=project,
                    region_code=region,
                    period_key=parse_period(col),
                    amount=amount,
                    currency=currency,
                )
            )
    return records


def long_dataframe_to_records(
    df: pd.DataFrame, *, default_currency: str = "USD"
) -> list[LongRecord]:
    """Normalize an already-LONG frame into :class:`LongRecord` objects (blanks skipped)."""
    records: list[LongRecord] = []
    for _, row in df.iterrows():
        amount = parse_amount(_str_cell(row, "amount"))
        if amount is None:  # blank amount -> NULL, skipped
            continue
        records.append(
            LongRecord(
                account_code=_str_cell(row, "account_code"),
                entity_code=_dim(row, "entity_code"),
                department_code=_dim(row, "department_code"),
                project_code=_dim(row, "project_code"),
                region_code=_dim(row, "region_code"),
                period_key=parse_period(_str_cell(row, "period")),
                amount=amount,
                currency=_currency(row, default_currency),
            )
        )
    return records
