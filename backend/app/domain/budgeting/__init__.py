"""Budgeting domain: four budget methods plus orthogonal modifiers (DESIGN.md section 2).

Pure FP&A logic with no FastAPI/DB imports. All money math is exact via ``decimal.Decimal``.
"""

from __future__ import annotations

from app.domain.budgeting.activity_based import ABBResult, Activity, activity_based_budget
from app.domain.budgeting.incremental import (
    BudgetLine,
    IncrementalLine,
    incremental_budget,
)
from app.domain.budgeting.modifiers import flexible_budget_allowance, rolling_horizon
from app.domain.budgeting.value_proposition import (
    FundingDecision,
    Initiative,
    value_proposition_budget,
)
from app.domain.budgeting.zero_based import (
    DecisionPackage,
    ZBBResult,
    zero_based_budget,
)

__all__ = [
    "ABBResult",
    "Activity",
    "BudgetLine",
    "DecisionPackage",
    "FundingDecision",
    "IncrementalLine",
    "Initiative",
    "ZBBResult",
    "activity_based_budget",
    "flexible_budget_allowance",
    "incremental_budget",
    "rolling_horizon",
    "value_proposition_budget",
    "zero_based_budget",
]
