"""Reporting domain — board-ready exports built from already-computed FP&A data.

Pure builders that take structured results and emit document bytes (no DB/network), so they are
fully unit-testable. Currently: the variance board pack (a formatted multi-tab Excel workbook).
"""

from __future__ import annotations

from app.domain.reporting.board_pack import (
    BoardRow,
    ReportMeta,
    build_board_pack,
)

__all__ = [
    "BoardRow",
    "ReportMeta",
    "build_board_pack",
]
