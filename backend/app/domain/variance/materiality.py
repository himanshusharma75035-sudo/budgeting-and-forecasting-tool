"""Materiality thresholding for variances (DESIGN.md 4.3).

A variance is flagged for attention only when it is *material*. Materiality uses a
**dual test** so that tiny absolute variances on a large base, and large-percentage
variances on a trivial base, are both filtered out: the variance must clear both an
absolute floor and a percentage-of-base hurdle.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

from app.domain.money import to_decimal


@dataclass(frozen=True)
class MaterialityThreshold:
    """Dual materiality threshold (DESIGN.md 4.3).

    Attributes:
        pct_threshold: minimum ``|variance / base|`` (e.g. ``0.10`` == 10%).
        abs_threshold: minimum ``|variance|`` in major currency units.
    """

    pct_threshold: float = 0.10
    abs_threshold: Decimal = field(default_factory=lambda: Decimal("0"))


def is_material(
    variance: Decimal,
    base: Decimal,
    threshold: MaterialityThreshold,
) -> bool:
    """Dual materiality test (DESIGN.md 4.3).

    Material when ``abs(variance) >= abs_threshold`` **and**
    (``base == 0`` **or** ``abs(variance / base) >= pct_threshold``).

    When ``base == 0`` the percentage hurdle is undefined and skipped, so the result is
    driven solely by the absolute floor: material iff ``abs(variance) >= abs_threshold``.
    """
    variance = to_decimal(variance)
    base = to_decimal(base)
    abs_variance = abs(variance)

    if abs_variance < to_decimal(threshold.abs_threshold):
        return False
    if base == 0:
        return True
    return abs(variance / base) >= to_decimal(threshold.pct_threshold)
