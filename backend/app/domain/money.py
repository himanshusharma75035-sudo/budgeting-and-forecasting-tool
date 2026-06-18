"""Money handling.

Money is stored as **integer minor units** (e.g. cents) — never float — because IEEE-754
cannot represent most decimals exactly and SQLite has no decimal type. See DESIGN.md 5.1.

Domain math (budgeting/forecasting/variance) operates in *major* units using ``Decimal`` for
exactness; conversion to/from minor units happens at the persistence boundary only.
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

Number = Decimal | int | float | str


def to_decimal(value: Number) -> Decimal:
    """Coerce to Decimal without binary-float surprises (floats go via str)."""
    if isinstance(value, Decimal):
        return value
    if isinstance(value, float):
        return Decimal(str(value))
    return Decimal(value)


def to_minor(value: Number, scale: int = 2) -> int:
    """Convert a major-unit amount to integer minor units, rounding half-up.

    >>> to_minor("231000.00")
    23100000
    >>> to_minor(Decimal("1.005"), 2)
    101
    """
    quant = Decimal(1).scaleb(-scale)  # 10**-scale
    cents = to_decimal(value).quantize(quant, rounding=ROUND_HALF_UP) * (10**scale)
    return int(cents.to_integral_value(rounding=ROUND_HALF_UP))


def from_minor(minor: int, scale: int = 2) -> Decimal:
    """Convert integer minor units back to a major-unit Decimal."""
    return (Decimal(minor) / (10**scale)).quantize(Decimal(1).scaleb(-scale))


def format_minor(minor: int, scale: int = 2, currency: str | None = None) -> str:
    """Human-readable amount, e.g. ``format_minor(23100000)`` -> ``'231000.00'``."""
    text = f"{from_minor(minor, scale):,.{scale}f}"
    return f"{currency} {text}" if currency else text
