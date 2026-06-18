"""Tests for the budgeting domain (DESIGN.md section 2).

Fixtures here are the VERIFIED synthetic fixtures from DESIGN.md 2.3-2.7.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from app.domain.budgeting import (
    Activity,
    DecisionPackage,
    IncrementalLine,
    Initiative,
    activity_based_budget,
    flexible_budget_allowance,
    incremental_budget,
    rolling_horizon,
    value_proposition_budget,
    zero_based_budget,
)

# --- Incremental (DESIGN.md 2.3) -------------------------------------------


def test_incremental_budget_fixture() -> None:
    # 200000 * 1.08 + 15000 = 231000
    lines = incremental_budget(
        [IncrementalLine("6100", Decimal("200000"), Decimal("0.08"), Decimal("15000"))]
    )
    assert len(lines) == 1
    assert lines[0].account_code == "6100"
    assert lines[0].name is None
    assert lines[0].amount == Decimal("231000.00")


def test_incremental_budget_defaults_no_growth_no_oneoff() -> None:
    lines = incremental_budget([IncrementalLine("6200", Decimal("50000"))])
    assert lines[0].amount == Decimal("50000")


# --- Activity-Based (DESIGN.md 2.4) ----------------------------------------


def test_activity_based_budget_fixture() -> None:
    # Full Decimal precision: 800*400000/700 + 16000*280000/15500 = 746175.1152...
    # DESIGN.md's worked 746,104 used display-rounded rates; we keep full precision.
    activities = [
        Activity("setup", Decimal("400000"), Decimal("700"), Decimal("800")),
        Activity("inspection", Decimal("280000"), Decimal("15500"), Decimal("16000")),
    ]
    result = activity_based_budget(activities, fixed_costs=Decimal("0"))
    assert len(result.lines) == 2
    assert result.lines[0].name == "setup"
    assert result.lines[0].account_code is None
    assert float(result.total) == pytest.approx(746175.12, abs=0.05)


def test_activity_based_budget_zero_units_raises() -> None:
    with pytest.raises(ValueError):
        activity_based_budget(
            [Activity("bad", Decimal("100"), Decimal("0"), Decimal("10"))]
        )


def test_activity_based_budget_includes_fixed_costs() -> None:
    result = activity_based_budget(
        [Activity("a", Decimal("100"), Decimal("10"), Decimal("10"))],
        fixed_costs=Decimal("250"),
    )
    # rate = 10, amount = 100, total = 100 + 250
    assert result.total == Decimal("350")
    assert result.fixed_costs == Decimal("250")


# --- Value-Proposition (DESIGN.md 2.5) -------------------------------------


def test_value_proposition_budget_fixture() -> None:
    # cap=100000; A(40k,90->2.25), B(30k,75->2.50), D(20k,50->2.50), C(50k,60->1.20)
    initiatives = [
        Initiative("A", Decimal("40000"), Decimal("90")),
        Initiative("B", Decimal("30000"), Decimal("75")),
        Initiative("D", Decimal("20000"), Decimal("50")),
        Initiative("C", Decimal("50000"), Decimal("60")),
    ]
    decision = value_proposition_budget(initiatives, cap=Decimal("100000"))
    assert set(decision.funded) == {"A", "B", "D"}
    assert decision.total_cost == Decimal("90000")
    assert decision.total_value == Decimal("215")
    assert decision.slack == Decimal("10000")
    assert decision.deferred == ["C"]


def test_value_proposition_budget_optimal_knapsack() -> None:
    # Same fixture; optimal mix should also be A+B+D (value 215) within the 100k cap.
    initiatives = [
        Initiative("A", Decimal("40000"), Decimal("90")),
        Initiative("B", Decimal("30000"), Decimal("75")),
        Initiative("D", Decimal("20000"), Decimal("50")),
        Initiative("C", Decimal("50000"), Decimal("60")),
    ]
    decision = value_proposition_budget(
        initiatives, cap=Decimal("100000"), optimal=True
    )
    assert set(decision.funded) == {"A", "B", "D"}
    assert decision.total_value == Decimal("215")
    assert decision.total_cost <= Decimal("100000")


# --- Zero-Based (DESIGN.md 2.6) --------------------------------------------


def test_zero_based_budget_fixture() -> None:
    # funds=250000; P1(120k,100->0.83), P2(60k,70->1.17), P3(90k,40->0.44), P4(80k,25->0.31)
    packages = [
        DecisionPackage("P1", Decimal("120000"), Decimal("100")),
        DecisionPackage("P2", Decimal("60000"), Decimal("70")),
        DecisionPackage("P3", Decimal("90000"), Decimal("40")),
        DecisionPackage("P4", Decimal("80000"), Decimal("25")),
    ]
    result = zero_based_budget(packages, total_funds=Decimal("250000"), rank_by="ratio")
    assert result.ranking == ["P2", "P1", "P3", "P4"]
    assert set(result.funded) == {"P1", "P2"}
    assert result.total_cost == Decimal("180000")
    assert result.remaining_funds == Decimal("70000")
    assert set(result.unfunded) == {"P3", "P4"}


def test_zero_based_budget_invalid_rank_by() -> None:
    with pytest.raises(ValueError):
        zero_based_budget(
            [DecisionPackage("P1", Decimal("10"), Decimal("5"))],
            total_funds=Decimal("100"),
            rank_by="bogus",
        )


# --- Modifiers (DESIGN.md 2.7) ---------------------------------------------


def test_flexible_budget_allowance() -> None:
    # 5 * 1000 + 20000 = 25000
    assert flexible_budget_allowance(
        Decimal("5"), Decimal("1000"), Decimal("20000")
    ) == Decimal("25000")


def test_rolling_horizon() -> None:
    assert rolling_horizon(202412, 3) == [202501, 202502, 202503]
