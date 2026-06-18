"""Monthly period-key utilities. A period key is a smart integer ``YYYYMM`` (e.g. 202601)."""

from __future__ import annotations

import calendar
import re

_MONTH_NAMES = list(calendar.month_name)  # index 1..12


def make_period_key(year: int, month: int) -> int:
    if not 1 <= month <= 12:
        raise ValueError(f"month out of range: {month}")
    return year * 100 + month


def split_period_key(key: int) -> tuple[int, int]:
    return divmod(key, 100)


def add_months(key: int, n: int) -> int:
    year, month = split_period_key(key)
    idx = (year * 12 + (month - 1)) + n
    return make_period_key(idx // 12, idx % 12 + 1)


def period_range(start_key: int, end_key: int) -> list[int]:
    """Inclusive list of monthly period keys from start to end."""
    if end_key < start_key:
        return []
    out, cur = [], start_key
    while cur <= end_key:
        out.append(cur)
        cur = add_months(cur, 1)
    return out


_PERIOD_RE = re.compile(r"^(\d{4})-(\d{2})(?:-\d{2})?$")


def parse_period(text: str) -> int:
    """Parse ``YYYY-MM`` or ``YYYY-MM-DD`` into a period key. Rejects ambiguous formats."""
    m = _PERIOD_RE.match(str(text).strip())
    if not m:
        raise ValueError(f"unrecognized period '{text}' (expected YYYY-MM or YYYY-MM-DD)")
    return make_period_key(int(m.group(1)), int(m.group(2)))


def format_period(key: int) -> str:
    year, month = split_period_key(key)
    return f"{year:04d}-{month:02d}"


def fiscal_attrs(key: int, fy_start_month: int = 1) -> dict[str, int]:
    """Derive fiscal year / quarter / period number from a calendar period key."""
    year, month = split_period_key(key)
    fiscal_period_num = (month - fy_start_month) % 12 + 1
    fiscal_year = year if month >= fy_start_month else year - 1
    if fy_start_month == 1:
        fiscal_year = year
    fiscal_quarter = (fiscal_period_num - 1) // 3 + 1
    calendar_quarter = (month - 1) // 3 + 1
    return {
        "fiscal_year": fiscal_year,
        "fiscal_quarter": fiscal_quarter,
        "fiscal_period_num": fiscal_period_num,
        "quarter": calendar_quarter,
    }


def month_bounds(key: int) -> tuple[str, str]:
    """ISO start/end date strings for the month."""
    year, month = split_period_key(key)
    last = calendar.monthrange(year, month)[1]
    return f"{year:04d}-{month:02d}-01", f"{year:04d}-{month:02d}-{last:02d}"


def month_name(key: int) -> str:
    _, month = split_period_key(key)
    return _MONTH_NAMES[month]
