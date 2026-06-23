"""Driver-based modeling domain (roadmap 0.2): drivers, a safe formula evaluator, and an engine
that evaluates a model over periods with same-period dependency ordering and cross-period ``prev()``.

Pure FP&A logic with no FastAPI/DB imports. Exact :class:`decimal.Decimal` math.
"""

from __future__ import annotations

from app.domain.drivers.engine import (
    AccountLine,
    Driver,
    DriverError,
    DriverEvaluation,
    DriverSeries,
    evaluate_model,
)
from app.domain.drivers.formula import FormulaError, evaluate, extract_references

__all__ = [
    "AccountLine",
    "Driver",
    "DriverError",
    "DriverEvaluation",
    "DriverSeries",
    "FormulaError",
    "evaluate",
    "evaluate_model",
    "extract_references",
]
