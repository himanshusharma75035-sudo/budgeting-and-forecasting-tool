"""Standard-costing cost variances (DESIGN.md 4.4).

All functions return a **signed** :class:`decimal.Decimal`. By the universal cost
convention a **positive** variance is *unfavorable* (actual cost exceeded standard) and a
**negative** variance is *favorable*. Use :func:`cost_variance_status` to classify.

Notation: AP/SP actual/standard price, AQ actual quantity, AQused actual quantity used,
SQ standard quantity allowed, AR/SR actual/standard rate, AH actual hours,
SH standard hours allowed.
"""

from __future__ import annotations

from decimal import Decimal

from app.domain.enums import VarianceStatus
from app.domain.money import to_decimal


def material_price_variance(
    actual_price: Decimal,
    std_price: Decimal,
    actual_qty: Decimal,
) -> Decimal:
    """Direct-material price variance (DESIGN.md 4.4): ``(AP - SP) * AQ``."""
    return (to_decimal(actual_price) - to_decimal(std_price)) * to_decimal(actual_qty)


def material_quantity_variance(
    actual_qty_used: Decimal,
    std_qty_allowed: Decimal,
    std_price: Decimal,
) -> Decimal:
    """Direct-material quantity/usage variance (DESIGN.md 4.4): ``(AQused - SQ) * SP``."""
    return (to_decimal(actual_qty_used) - to_decimal(std_qty_allowed)) * to_decimal(std_price)


def labor_rate_variance(
    actual_rate: Decimal,
    std_rate: Decimal,
    actual_hours: Decimal,
) -> Decimal:
    """Direct-labor rate variance (DESIGN.md 4.4): ``(AR - SR) * AH``."""
    return (to_decimal(actual_rate) - to_decimal(std_rate)) * to_decimal(actual_hours)


def labor_efficiency_variance(
    actual_hours: Decimal,
    std_hours_allowed: Decimal,
    std_rate: Decimal,
) -> Decimal:
    """Direct-labor efficiency variance (DESIGN.md 4.4): ``(AH - SH) * SR``."""
    return (to_decimal(actual_hours) - to_decimal(std_hours_allowed)) * to_decimal(std_rate)


def voh_spending_variance(
    actual_rate: Decimal,
    std_rate: Decimal,
    actual_hours: Decimal,
) -> Decimal:
    """Variable-overhead spending variance (DESIGN.md 4.4): ``(AR - SR) * AH``."""
    return (to_decimal(actual_rate) - to_decimal(std_rate)) * to_decimal(actual_hours)


def voh_efficiency_variance(
    actual_hours: Decimal,
    std_hours_allowed: Decimal,
    std_rate: Decimal,
) -> Decimal:
    """Variable-overhead efficiency variance (DESIGN.md 4.4): ``(AH - SH) * SR``."""
    return (to_decimal(actual_hours) - to_decimal(std_hours_allowed)) * to_decimal(std_rate)


def fixed_oh_spending_variance(
    actual_foh: Decimal,
    budgeted_foh: Decimal,
) -> Decimal:
    """Fixed-overhead spending (budget) variance (DESIGN.md 4.4): ``actual_foh - budgeted_foh``."""
    return to_decimal(actual_foh) - to_decimal(budgeted_foh)


def fixed_oh_volume_variance(
    std_foh_rate_per_unit: Decimal,
    budgeted_units: Decimal,
    actual_units: Decimal,
) -> Decimal:
    """Fixed-overhead production-volume variance (DESIGN.md 4.4).

    Formula: ``std_foh_rate_per_unit * (budgeted_units - actual_units)``.

    VERIFIED direction is **Budgeted FOH - Applied FOH**. When actual production exceeds
    the budgeted (denominator) level, fixed overhead is *over-absorbed*, the variance is
    **negative => Favorable**; under-production *under-absorbs* and yields a positive
    (Unfavorable) variance.

    NOTE: this is a non-cash absorption-costing capacity artifact reflecting how fixed
    overhead was spread over volume, not a change in cash spending. It should be
    **excluded from spend dashboards** (use :func:`fixed_oh_spending_variance` for the
    cash view).
    """
    rate = to_decimal(std_foh_rate_per_unit)
    return rate * (to_decimal(budgeted_units) - to_decimal(actual_units))


def cost_variance_status(variance: Decimal) -> VarianceStatus:
    """Classify a signed cost variance (DESIGN.md 4.4).

    Positive => UNFAVORABLE, negative => FAVORABLE, exactly zero => NEUTRAL.
    """
    variance = to_decimal(variance)
    if variance > 0:
        return VarianceStatus.UNFAVORABLE
    if variance < 0:
        return VarianceStatus.FAVORABLE
    return VarianceStatus.NEUTRAL
