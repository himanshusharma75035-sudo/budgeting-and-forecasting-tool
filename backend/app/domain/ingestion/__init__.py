"""Data ingestion domain (DESIGN.md 5.4).

Pure, dependency-free parsing/validation/pivot for the WIDE (Excel-style) and LONG
(ERP-feed) upload templates. The pipeline is: :func:`read_table` -> :func:`detect_layout`
-> ``validate_*`` (per-row :class:`ValidationReport`) -> ``pivot_wide_to_long`` /
``long_dataframe_to_records`` producing tidy :class:`LongRecord` rows for UPSERT. Template
builders back the download endpoint. No FastAPI/DB imports live here; money is exact
:class:`~decimal.Decimal` and periods are smart-integer ``YYYYMM`` keys.
"""

from __future__ import annotations

from app.domain.ingestion.parser import (
    LONG_COLS,
    PERIOD_COL_RE,
    WIDE_ID_COLS,
    detect_layout,
    period_columns,
    read_table,
)
from app.domain.ingestion.pivot import (
    LongRecord,
    long_dataframe_to_records,
    pivot_wide_to_long,
)
from app.domain.ingestion.template import (
    build_long_template,
    build_wide_template,
    long_template_csv,
    wide_template_csv,
)
from app.domain.ingestion.validator import (
    RowError,
    ValidationReport,
    parse_amount,
    validate_long,
    validate_wide,
)

__all__ = [
    # parser
    "WIDE_ID_COLS",
    "LONG_COLS",
    "PERIOD_COL_RE",
    "read_table",
    "detect_layout",
    "period_columns",
    # validator
    "parse_amount",
    "RowError",
    "ValidationReport",
    "validate_wide",
    "validate_long",
    # pivot
    "LongRecord",
    "pivot_wide_to_long",
    "long_dataframe_to_records",
    # template
    "build_wide_template",
    "wide_template_csv",
    "build_long_template",
    "long_template_csv",
]
