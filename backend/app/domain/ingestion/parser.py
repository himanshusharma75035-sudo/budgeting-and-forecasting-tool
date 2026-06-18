"""CSV/Excel table reading and layout detection (DESIGN.md 5.4).

The upload template comes in two shapes:

* **WIDE** (the default Excel/CSV finance teams build): identifier columns followed by
  one numeric column per period named ``YYYY-MM``.
* **LONG** (ERP/system feeds): one row per fact with an explicit ``period`` + ``amount``.

This module is the typeless front door. Everything is read as **strings**
(``dtype=str``) so that downstream validation owns numeric/date coercion -- CSV has no
types and Excel's auto-typing would silently mangle codes like account ``00400`` or
re-interpret period headers as dates.
"""

from __future__ import annotations

import io
import re
from pathlib import Path

import pandas as pd

# WIDE template identifier columns, in canonical order (DESIGN.md 5.4).
WIDE_ID_COLS = [
    "account_code",
    "account_name",
    "entity_code",
    "department_code",
    "project_code",
    "region_code",
    "currency",
]

# LONG template columns, in canonical order (DESIGN.md 5.4).
LONG_COLS = [
    "account_code",
    "entity_code",
    "department_code",
    "project_code",
    "region_code",
    "period",
    "amount",
    "currency",
]

# A period column / value is exactly ``YYYY-MM`` (DESIGN.md 5.4).
PERIOD_COL_RE = re.compile(r"^\d{4}-\d{2}$")


def read_table(data: bytes | str | Path, filename: str) -> pd.DataFrame:
    """Read an uploaded CSV/XLSX/XLS into an all-string DataFrame.

    ``data`` may be raw ``bytes`` (an upload body), file *text* (``str`` for CSV), or a
    filesystem :class:`~pathlib.Path`. ``filename`` selects the reader by extension.
    Blanks are preserved as empty strings (``keep_default_na=False``) so the validator can
    distinguish a true blank (NULL) from the literal string ``"NaN"``. Column-name
    whitespace is stripped.
    """
    suffix = Path(filename).suffix.lower()
    if suffix == ".csv":
        source: io.StringIO | io.BytesIO | Path
        if isinstance(data, bytes):
            source = io.StringIO(data.decode("utf-8-sig"))
        elif isinstance(data, Path):
            source = data
        else:
            source = io.StringIO(data)
        df = pd.read_csv(source, dtype=str, keep_default_na=False)
    elif suffix in (".xlsx", ".xls"):
        excel_source: io.BytesIO | Path
        if isinstance(data, bytes):
            excel_source = io.BytesIO(data)
        elif isinstance(data, Path):
            excel_source = data
        else:  # a str path to an Excel file
            excel_source = Path(data)
        df = pd.read_excel(excel_source, engine="calamine", dtype=str)
    else:
        raise ValueError(f"unsupported upload extension '{suffix}' (expected .csv/.xlsx/.xls)")

    df.columns = [str(c).strip() for c in df.columns]
    return df


def detect_layout(df: pd.DataFrame) -> str:
    """Return ``"WIDE"`` if any column is a ``YYYY-MM`` period header, else ``"LONG"``."""
    if any(PERIOD_COL_RE.match(str(c)) for c in df.columns):
        return "WIDE"
    return "LONG"


def period_columns(df: pd.DataFrame) -> list[str]:
    """Return the ``YYYY-MM`` period columns of a WIDE frame, in column order."""
    return [str(c) for c in df.columns if PERIOD_COL_RE.match(str(c))]
