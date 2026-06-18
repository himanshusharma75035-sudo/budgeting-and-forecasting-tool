"""Tests for the variance analysis domain (DESIGN.md 4).

Fixtures here were adversarially verified; the expected values are intentionally exact.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from app.domain.enums import AccountType, VarianceStatus
from app.domain.variance import (
    BridgeStep,
    MaterialityThreshold,
    ProductSales,
    budget_vs_actual,
    build_bridge,
    cost_variance_status,
    favorable_variance,
    fixed_oh_spending_variance,
    fixed_oh_volume_variance,
    is_favorable,
    is_material,
    labor_efficiency_variance,
    labor_rate_variance,
    material_price_variance,
    material_quantity_variance,
    price_volume_decomposition,
    sales_mix_quantity,
    status,
    variance_hierarchy,
)

# --- sign / polarity -------------------------------------------------------


def test_is_favorable_cost_negative_is_favorable() -> None:
    assert is_favorable(AccountType.OPEX, Decimal("-6000")) is True


def test_is_favorable_revenue_negative_is_unfavorable() -> None:
    assert is_favorable(AccountType.REVENUE, Decimal("-6000")) is False


def test_favorable_variance_orients_cost_to_negative() -> None:
    assert favorable_variance(AccountType.OPEX, Decimal("5000")) == Decimal("-5000")


def test_favorable_variance_revenue_unchanged() -> None:
    assert favorable_variance(AccountType.REVENUE, Decimal("5000")) == Decimal("5000")


def test_status_neutral_within_eps() -> None:
    assert status(AccountType.OPEX, Decimal("50"), neutral_eps=Decimal("100")) is VarianceStatus.NEUTRAL


def test_status_favorable_for_cost_saving() -> None:
    assert status(AccountType.OPEX, Decimal("-6000")) is VarianceStatus.FAVORABLE


# --- budget vs actual ------------------------------------------------------


def test_budget_vs_actual_opex_favorable() -> None:
    result = budget_vs_actual(Decimal("225000"), Decimal("231000"), AccountType.OPEX)
    assert result.variance == Decimal("-6000")
    assert result.status is VarianceStatus.FAVORABLE
    assert result.favorable is True
    assert result.variance_pct == pytest.approx(-2.5974, abs=1e-3)


def test_budget_vs_actual_zero_comparison_pct_none() -> None:
    result = budget_vs_actual(Decimal("100"), Decimal("0"), AccountType.REVENUE)
    assert result.variance_pct is None
    assert result.variance == Decimal("100")


# --- flexible budget hierarchy --------------------------------------------


def test_variance_hierarchy_invariant_and_values() -> None:
    h = variance_hierarchy(
        actual=Decimal("520000"),
        flexible=Decimal("500000"),
        static=Decimal("460000"),
    )
    assert h.static_variance == Decimal("60000")
    assert h.flexible_budget_variance == Decimal("20000")
    assert h.sales_volume_variance == Decimal("40000")
    assert h.static_variance == h.flexible_budget_variance + h.sales_volume_variance


# --- cost variances --------------------------------------------------------


def test_material_price_variance() -> None:
    assert material_price_variance(Decimal("1.20"), Decimal("1.00"), Decimal("440000")) == Decimal("88000.00")


def test_material_quantity_variance() -> None:
    assert material_quantity_variance(Decimal("399000"), Decimal("420000"), Decimal("1.00")) == Decimal("-21000")


def test_labor_rate_variance() -> None:
    assert labor_rate_variance(Decimal("15"), Decimal("13"), Decimal("18900")) == Decimal("37800")


def test_labor_efficiency_variance() -> None:
    assert labor_efficiency_variance(Decimal("18900"), Decimal("21000"), Decimal("13")) == Decimal("-27300")


def test_fixed_oh_spending_variance() -> None:
    assert fixed_oh_spending_variance(Decimal("136000"), Decimal("140280")) == Decimal("-4280")


def test_fixed_oh_volume_variance_overproduction_favorable() -> None:
    # Over-production over-absorbs FOH => negative => Favorable.
    assert fixed_oh_volume_variance(Decimal("0.70"), Decimal("200400"), Decimal("210000")) == Decimal("-6720")


def test_cost_variance_status_positive_is_unfavorable() -> None:
    assert cost_variance_status(Decimal("88000.00")) is VarianceStatus.UNFAVORABLE


def test_cost_variance_status_negative_is_favorable() -> None:
    assert cost_variance_status(Decimal("-4280")) is VarianceStatus.FAVORABLE


def test_cost_variance_status_zero_is_neutral() -> None:
    assert cost_variance_status(Decimal("0")) is VarianceStatus.NEUTRAL


# --- sales mix / quantity --------------------------------------------------


def test_sales_mix_quantity_reconciliation() -> None:
    products = [
        ProductSales("X", actual_units=Decimal("700"), budgeted_units=Decimal("500"), budgeted_cm_per_unit=Decimal("10")),
        ProductSales("Y", actual_units=Decimal("400"), budgeted_units=Decimal("500"), budgeted_cm_per_unit=Decimal("20")),
    ]
    result = sales_mix_quantity(products)

    assert result.mix["X"] == Decimal("1500")
    assert result.mix["Y"] == Decimal("-3000")
    assert result.quantity["X"] == Decimal("500")
    assert result.quantity["Y"] == Decimal("1000")

    # Per-product invariant: mix + quantity == single-product sales-volume variance.
    for p in products:
        expected_volume = (p.actual_units - p.budgeted_units) * p.budgeted_cm_per_unit
        assert result.mix[p.name] + result.quantity[p.name] == expected_volume

    # Totals reconcile.
    assert result.total_mix + result.total_quantity == result.total_volume
    assert result.total_volume == Decimal("0")


def test_sales_mix_quantity_zero_budget_raises() -> None:
    products = [
        ProductSales("X", actual_units=Decimal("10"), budgeted_units=Decimal("0"), budgeted_cm_per_unit=Decimal("5")),
    ]
    with pytest.raises(ValueError):
        sales_mix_quantity(products)


# --- materiality -----------------------------------------------------------


def test_is_material_dual_test_passes() -> None:
    threshold = MaterialityThreshold(pct_threshold=0.10, abs_threshold=Decimal("1000"))
    # 30000 / 231000 ~= 13% >= 10% AND 30000 >= 1000: clears both hurdles -> material.
    assert is_material(Decimal("30000"), Decimal("231000"), threshold) is True


def test_is_material_fails_pct_hurdle() -> None:
    threshold = MaterialityThreshold(pct_threshold=0.10, abs_threshold=Decimal("1000"))
    # 2000 / 231000 ~= 0.9% < 10%: a small variance on a large base clears the absolute
    # floor but fails the percentage hurdle, so it is not material.
    assert is_material(Decimal("2000"), Decimal("231000"), threshold) is False


def test_is_material_fails_abs_floor() -> None:
    threshold = MaterialityThreshold(pct_threshold=0.10, abs_threshold=Decimal("1000"))
    assert is_material(Decimal("500"), Decimal("100"), threshold) is False


def test_is_material_zero_base_uses_abs_only() -> None:
    threshold = MaterialityThreshold(pct_threshold=0.10, abs_threshold=Decimal("1000"))
    assert is_material(Decimal("1500"), Decimal("0"), threshold) is True
    assert is_material(Decimal("500"), Decimal("0"), threshold) is False


# --- bridge / PVM ----------------------------------------------------------


def test_build_bridge_sums_deltas() -> None:
    bridge = build_bridge(
        Decimal("1000"),
        [BridgeStep("price", Decimal("220")), BridgeStep("volume", Decimal("220"))],
    )
    assert bridge.end == Decimal("1440")
    assert [s.label for s in bridge.steps] == ["price", "volume"]


def test_price_volume_decomposition_reconciles() -> None:
    price_effect, volume_effect = price_volume_decomposition(
        budget_price=Decimal("10"),
        actual_price=Decimal("12"),
        budget_qty=Decimal("100"),
        actual_qty=Decimal("120"),
    )
    assert price_effect == Decimal("220")
    assert volume_effect == Decimal("220")
    total = Decimal("12") * Decimal("120") - Decimal("10") * Decimal("100")
    assert price_effect + volume_effect == total == Decimal("440")
