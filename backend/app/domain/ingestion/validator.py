"""Per-row validation of uploaded WIDE/LONG tables (DESIGN.md 5.4).

Validation is **fail-fast per row**: each problem is recorded as a :class:`RowError`
against a 1-based data-row index (the header is row 0) so the API can return a precise,
human-readable error report rather than aborting the whole upload on the first issue.

The checks here are purely about *shape and referential validity* of the raw cells:
required columns present, account/dimension codes resolve to known members, periods are
ISO ``YYYY-MM``/``YYYY-MM-DD``, numeric cells parse, and no in-file duplicate natural
keys. Money never becomes a float -- amounts are parsed to :class:`~decimal.Decimal`.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation

import pandas as pd

from app.domain.ingestion.parser import period_columns
from app.domain.money import to_decimal
from app.domain.periods import parse_period

# Dimension columns that carry referential codes (account_code is checked separately).
_DIM_COLS = ["entity_code", "department_code", "project_code", "region_code"]

# A valid numeric cell: optional leading '-', digits, optional single '.' decimal.
_NUMERIC_RE = re.compile(r"^-?\d+(\.\d+)?$")


def parse_amount(raw: object) -> Decimal | None:
    """Parse one numeric cell into a :class:`~decimal.Decimal`, or ``None`` for blank.

    Blank semantics (DESIGN.md 5.4): ``None`` / ``NaN`` / ``""`` / whitespace -> ``None``
    (NULL, **not** zero). Already-numeric ``int``/``float`` pass through. Strings must be a
    plain number -- no currency symbols, no thousands separators (comma), no ``%``, no
    parentheses; a single optional ``-`` sign and a single ``.`` decimal only. Anything
    else raises :class:`ValueError`.
    """
    if raw is None:
        return None
    if isinstance(raw, bool):  # guard: bool is an int subclass, never a valid amount
        raise ValueError(f"invalid amount {raw!r}")
    if isinstance(raw, int):
        return to_decimal(raw)
    if isinstance(raw, float):
        if math.isnan(raw):
            return None
        return to_decimal(raw)
    if isinstance(raw, Decimal):
        return raw

    text = str(raw).strip()
    if text == "":
        return None
    if not _NUMERIC_RE.match(text):
        raise ValueError(
            f"invalid amount '{text}': use a plain number (no symbols, %, commas, "
            "parentheses; '.' decimal only)"
        )
    try:
        return to_decimal(text)
    except InvalidOperation as exc:  # pragma: no cover - regex already guards this
        raise ValueError(f"invalid amount '{text}'") from exc


@dataclass(frozen=True)
class RowError:
    """A single validation failure tied to a 1-based data row (header is row 0)."""

    row: int
    field: str
    message: str


@dataclass
class ValidationReport:
    """Aggregate outcome of validating one uploaded table."""

    layout: str
    rows_total: int
    rows_ok: int
    errors: list[RowError] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        """True when no row produced an error."""
        return not self.errors


def _cell(row: pd.Series, column: str) -> str:
    """Return a stripped string cell, treating NaN/None as empty."""
    if column not in row:
        return ""
    value = row[column]
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return ""
    return str(value).strip()


def _check_dims(
    row: pd.Series,
    rownum: int,
    known_dim_codes: dict[str, set[str]],
    errors: list[RowError],
) -> bool:
    """Validate provided dimension codes against their known sets. Returns ok flag."""
    row_ok = True
    for col in _DIM_COLS:
        if col not in row.index or col not in known_dim_codes:
            continue
        code = _cell(row, col)
        if code and code not in known_dim_codes[col]:
            errors.append(RowError(rownum, col, f"unknown {col} '{code}'"))
            row_ok = False
    return row_ok


def _natural_key(row: pd.Series, period: str) -> tuple[str, ...]:
    """The in-file uniqueness key: account_code + dimension codes + period."""
    return (
        _cell(row, "account_code"),
        _cell(row, "entity_code"),
        _cell(row, "department_code"),
        _cell(row, "project_code"),
        _cell(row, "region_code"),
        period,
    )


def validate_wide(
    df: pd.DataFrame,
    known_account_codes: set[str],
    known_dim_codes: dict[str, set[str]],
) -> ValidationReport:
    """Validate a WIDE frame (identifier columns + ``YYYY-MM`` period columns)."""
    errors: list[RowError] = []
    rows_total = len(df)

    if "account_code" not in df.columns:
        errors.append(RowError(0, "account_code", "missing required column 'account_code'"))
        return ValidationReport("WIDE", rows_total, 0, errors)

    periods = period_columns(df)
    if not periods:
        errors.append(RowError(0, "period", "no period columns (expected YYYY-MM headers)"))

    seen: dict[tuple[str, ...], int] = {}
    rows_ok = 0
    for idx, (_, row) in enumerate(df.iterrows(), start=1):
        row_ok = True
        account = _cell(row, "account_code")
        if not account:
            errors.append(RowError(idx, "account_code", "missing account_code"))
            row_ok = False
        elif account not in known_account_codes:
            errors.append(RowError(idx, "account_code", f"unknown account_code '{account}'"))
            row_ok = False

        if not _check_dims(row, idx, known_dim_codes, errors):
            row_ok = False

        for col in periods:
            raw = _cell(row, col)
            if raw == "":
                continue
            try:
                parse_amount(raw)
            except ValueError as exc:
                errors.append(RowError(idx, col, str(exc)))
                row_ok = False

        # Duplicate natural keys: one key per non-blank period cell.
        for col in periods:
            if _cell(row, col) == "":
                continue
            key = _natural_key(row, col)
            if key in seen:
                errors.append(
                    RowError(idx, col, f"duplicate natural key (also row {seen[key]})")
                )
                row_ok = False
            else:
                seen[key] = idx

        if row_ok:
            rows_ok += 1

    return ValidationReport("WIDE", rows_total, rows_ok, errors)


def validate_long(
    df: pd.DataFrame,
    known_account_codes: set[str],
    known_dim_codes: dict[str, set[str]],
) -> ValidationReport:
    """Validate a LONG frame (one fact row per account/dim/period)."""
    errors: list[RowError] = []
    rows_total = len(df)

    missing = [c for c in ("account_code", "period", "amount") if c not in df.columns]
    if missing:
        for col in missing:
            errors.append(RowError(0, col, f"missing required column '{col}'"))
        return ValidationReport("LONG", rows_total, 0, errors)

    seen: dict[tuple[str, ...], int] = {}
    rows_ok = 0
    for idx, (_, row) in enumerate(df.iterrows(), start=1):
        row_ok = True
        account = _cell(row, "account_code")
        if not account:
            errors.append(RowError(idx, "account_code", "missing account_code"))
            row_ok = False
        elif account not in known_account_codes:
            errors.append(RowError(idx, "account_code", f"unknown account_code '{account}'"))
            row_ok = False

        if not _check_dims(row, idx, known_dim_codes, errors):
            row_ok = False

        period_text = _cell(row, "period")
        period_norm = ""
        if not period_text:
            errors.append(RowError(idx, "period", "missing period"))
            row_ok = False
        else:
            try:
                period_norm = str(parse_period(period_text))
            except ValueError as exc:
                errors.append(RowError(idx, "period", str(exc)))
                row_ok = False

        try:
            parse_amount(_cell(row, "amount"))
        except ValueError as exc:
            errors.append(RowError(idx, "amount", str(exc)))
            row_ok = False

        if period_norm:
            key = _natural_key(row, period_norm)
            if key in seen:
                errors.append(
                    RowError(idx, "period", f"duplicate natural key (also row {seen[key]})")
                )
                row_ok = False
            else:
                seen[key] = idx

        if row_ok:
            rows_ok += 1

    return ValidationReport("LONG", rows_total, rows_ok, errors)


__all__ = [
    "RowError",
    "ValidationReport",
    "parse_amount",
    "validate_long",
    "validate_wide",
]
