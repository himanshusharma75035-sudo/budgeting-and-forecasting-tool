"""Driver-based modeling engine — the analytical heart of FP&A planning.

A *driver model* is a set of named drivers evaluated over an ordered list of periods. Each driver
is either an **INPUT** (an explicit value per period) or a **FORMULA** (an expression over other
drivers, optionally referencing prior periods via ``prev()``). Drivers may map to an ``account_code``
so the model yields budget/forecast lines per account per period.

Evaluation:

1. Build a dependency graph from each formula's *same-period* references.
2. Topologically sort it — raising :class:`DriverError` on cycles or unknown references.
3. Evaluate period by period in dependency order. Cross-period ``prev()`` references read
   already-computed history, so they never create a cycle (``revenue = prev(revenue) * 1.1`` is fine).

Pure FP&A logic: no FastAPI/DB imports, exact :class:`decimal.Decimal` math.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from decimal import Decimal

from app.domain.drivers.formula import FormulaError, PrevFn, evaluate, extract_references
from app.domain.enums import DriverKind
from app.domain.money import to_decimal


class DriverError(ValueError):
    """Raised for structural problems in a driver model (cycles, duplicates, unknown refs)."""


@dataclass(frozen=True)
class Driver:
    """A single driver: an INPUT (explicit per-period ``values``) or a FORMULA."""

    code: str
    name: str
    kind: DriverKind
    formula: str | None = None
    values: Mapping[str, Decimal] = field(default_factory=dict)
    account_code: str | None = None
    unit: str | None = None


@dataclass(frozen=True)
class DriverSeries:
    """A driver's evaluated value at each model period (aligned to ``DriverEvaluation.periods``)."""

    code: str
    name: str
    kind: DriverKind
    unit: str | None
    account_code: str | None
    points: list[Decimal]


@dataclass(frozen=True)
class AccountLine:
    """Summed contribution of all drivers mapped to one account, per period."""

    account_code: str
    points: list[Decimal]
    total: Decimal


@dataclass(frozen=True)
class DriverEvaluation:
    periods: list[str]
    series: list[DriverSeries]
    account_lines: list[AccountLine]


def evaluate_model(drivers: Sequence[Driver], periods: Sequence[str]) -> DriverEvaluation:
    """Evaluate a driver model over ``periods`` (ordered, e.g. ``["2026-01", "2026-02", ...]``)."""
    period_list = list(periods)
    by_code: dict[str, Driver] = {}
    for d in drivers:
        if d.code in by_code:
            raise DriverError(f"duplicate driver code: {d.code!r}")
        by_code[d.code] = d

    order = _topo_order(by_code)
    history: dict[str, list[Decimal]] = {code: [] for code in by_code}

    for i, period in enumerate(period_list):
        prev_fn = _make_prev(history, i)
        context: dict[str, Decimal] = {}
        for code in order:
            d = by_code[code]
            if d.kind == DriverKind.INPUT:
                value = to_decimal(d.values.get(period, Decimal("0")))
            else:
                if not d.formula:
                    raise DriverError(f"formula driver {code!r} has no formula")
                raw = evaluate(d.formula, context, prev_fn)
                value = (Decimal(1) if raw else Decimal(0)) if isinstance(raw, bool) else raw
            context[code] = value
            history[code].append(value)

    series = [
        DriverSeries(
            code=d.code,
            name=d.name,
            kind=d.kind,
            unit=d.unit,
            account_code=d.account_code,
            points=list(history[d.code]),
        )
        for d in by_code.values()
    ]
    account_lines = _account_lines(drivers, history, len(period_list))
    return DriverEvaluation(periods=period_list, series=series, account_lines=account_lines)


def _make_prev(history: dict[str, list[Decimal]], idx: int) -> PrevFn:
    def prev(code: str, n: int = 1) -> Decimal:
        if n < 1:
            raise FormulaError("prev() offset must be >= 1")
        if code not in history:
            raise FormulaError(f"prev() references unknown driver: {code!r}")
        j = idx - n
        return history[code][j] if j >= 0 else Decimal("0")

    return prev


def _topo_order(by_code: Mapping[str, Driver]) -> list[str]:
    deps: dict[str, set[str]] = {}
    for code, d in by_code.items():
        refs = extract_references(d.formula) if d.kind == DriverKind.FORMULA and d.formula else set()
        for r in refs:
            if r not in by_code:
                raise DriverError(f"driver {code!r} references unknown driver {r!r}")
        deps[code] = refs

    order: list[str] = []
    state: dict[str, int] = {}  # 0=unvisited, 1=visiting, 2=done

    def visit(code: str, stack: tuple[str, ...]) -> None:
        seen = state.get(code, 0)
        if seen == 2:
            return
        if seen == 1:
            raise DriverError(f"cyclic driver dependency: {' -> '.join((*stack, code))}")
        state[code] = 1
        for dep in sorted(deps[code]):
            visit(dep, (*stack, code))
        state[code] = 2
        order.append(code)

    for code in by_code:
        visit(code, ())
    return order


def _account_lines(
    drivers: Sequence[Driver], history: Mapping[str, list[Decimal]], n_periods: int
) -> list[AccountLine]:
    acct_points: dict[str, list[Decimal]] = {}
    for d in drivers:
        if not d.account_code:
            continue
        points = acct_points.setdefault(d.account_code, [Decimal("0")] * n_periods)
        for i in range(n_periods):
            points[i] += history[d.code][i]
    return [
        AccountLine(account_code=ac, points=points, total=sum(points, Decimal("0")))
        for ac, points in sorted(acct_points.items())
    ]
