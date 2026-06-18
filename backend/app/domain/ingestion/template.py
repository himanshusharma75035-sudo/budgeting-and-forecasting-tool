"""Blank upload-template builders for the download endpoint (DESIGN.md 5.4).

These produce the empty WIDE/LONG templates a finance user downloads, fills in, and
re-uploads. The WIDE template has one row per postable account with blank period cells and
sensible dimension defaults pre-filled so the common single-entity case needs no edits. The
LONG template carries a couple of example rows to demonstrate the row-per-fact shape.
"""

from __future__ import annotations

import pandas as pd

from app.domain.ingestion.parser import LONG_COLS, WIDE_ID_COLS

# Dimension defaults pre-filled into a blank WIDE template (DESIGN.md 5.4).
_DEFAULT_ENTITY = "HQ"
_DEFAULT_DEPARTMENT = "UNALLOC"
_DEFAULT_PROJECT = "NONE"
_DEFAULT_REGION = "ALL"
_DEFAULT_CURRENCY = "USD"


def build_wide_template(
    accounts: list[tuple[str, str]], period_labels: list[str]
) -> pd.DataFrame:
    """Build a blank WIDE template DataFrame.

    ``accounts`` is a list of ``(account_code, account_name)`` pairs; ``period_labels`` are
    ``YYYY-MM`` strings used as the trailing numeric columns. Period cells are empty.
    """
    columns = [*WIDE_ID_COLS, *period_labels]
    rows: list[dict[str, str]] = []
    for code, name in accounts:
        row: dict[str, str] = {
            "account_code": code,
            "account_name": name,
            "entity_code": _DEFAULT_ENTITY,
            "department_code": _DEFAULT_DEPARTMENT,
            "project_code": _DEFAULT_PROJECT,
            "region_code": _DEFAULT_REGION,
            "currency": _DEFAULT_CURRENCY,
        }
        for label in period_labels:
            row[label] = ""
        rows.append(row)
    return pd.DataFrame(rows, columns=columns)


def wide_template_csv(accounts: list[tuple[str, str]], period_labels: list[str]) -> str:
    """Render :func:`build_wide_template` as CSV text."""
    return build_wide_template(accounts, period_labels).to_csv(index=False)


def build_long_template(
    accounts: list[tuple[str, str]], period_labels: list[str]
) -> pd.DataFrame:
    """Build a LONG template DataFrame with a few example rows.

    One example row is emitted per ``(account, period)`` combination (capped to keep the
    sample small) with empty amounts, demonstrating the row-per-fact shape.
    """
    rows: list[dict[str, str]] = []
    for code, _name in accounts:
        for label in period_labels:
            rows.append(
                {
                    "account_code": code,
                    "entity_code": _DEFAULT_ENTITY,
                    "department_code": _DEFAULT_DEPARTMENT,
                    "project_code": _DEFAULT_PROJECT,
                    "region_code": _DEFAULT_REGION,
                    "period": label,
                    "amount": "",
                    "currency": _DEFAULT_CURRENCY,
                }
            )
    return pd.DataFrame(rows, columns=LONG_COLS)


def long_template_csv(accounts: list[tuple[str, str]], period_labels: list[str]) -> str:
    """Render :func:`build_long_template` as CSV text."""
    return build_long_template(accounts, period_labels).to_csv(index=False)
