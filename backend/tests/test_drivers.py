"""Tests for driver-based modeling: the safe formula evaluator, the engine, and the API."""

from __future__ import annotations

from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from app.domain.drivers import (
    Driver,
    DriverError,
    FormulaError,
    evaluate,
    evaluate_model,
    extract_references,
)
from app.domain.enums import DriverKind
from app.main import app

D = Decimal


# --- formula evaluator -----------------------------------------------------


def test_arithmetic_and_references() -> None:
    ctx = {"price": D("100"), "volume": D("1000")}
    assert evaluate("price * volume", ctx) == D("100000")
    assert evaluate("price * volume * 0.4", ctx) == D("40000")
    assert evaluate("(price - 10) * volume", ctx) == D("90000")
    assert evaluate("-price", ctx) == D("-100")


def test_functions() -> None:
    ctx = {"a": D("3"), "b": D("9")}
    assert evaluate("min(a, b)", ctx) == D("3")
    assert evaluate("max(a, b)", ctx) == D("9")
    assert evaluate("abs(a - b)", ctx) == D("6")
    assert evaluate("round(2.5)", {}) == D("3")  # half-up
    assert evaluate("round(123.456, 2)", {}) == D("123.46")


def test_conditionals_and_comparisons() -> None:
    assert evaluate("10 if x > 0 else 0", {"x": D("5")}) == D("10")
    assert evaluate("10 if x > 0 else 0", {"x": D("-5")}) == D("0")
    assert evaluate("x > 0 and x < 100", {"x": D("50")}) is True
    assert evaluate("x > 0 and x < 100", {"x": D("150")}) is False
    assert evaluate("1 < 2 < 3", {}) is True  # chained


def test_extract_references_excludes_prev_and_funcs() -> None:
    assert extract_references("price * volume") == {"price", "volume"}
    assert extract_references("min(a, b) + c") == {"a", "b", "c"}
    # prev()'s first arg is a prior-period ref, not a same-period dependency
    assert extract_references("prev(revenue) * (1 + growth)") == {"growth"}


@pytest.mark.parametrize(
    "expr",
    [
        "__import__('os')",  # call to non-whitelisted name
        "obj.attr",  # attribute access
        "data[0]",  # subscript
        "[x for x in y]",  # comprehension
        "(lambda: 1)()",  # lambda
        "1 ; 2",  # statement / syntax error in eval mode
        "open('f')",  # unknown function
    ],
)
def test_unsafe_or_malformed_rejected(expr: str) -> None:
    with pytest.raises(FormulaError):
        evaluate(expr, {})


def test_unknown_reference_and_div_zero() -> None:
    with pytest.raises(FormulaError):
        evaluate("missing + 1", {})
    with pytest.raises(FormulaError):
        evaluate("a / 0", {"a": D("1")})


# --- engine ----------------------------------------------------------------


def _series(ev, code: str) -> list[Decimal]:
    return next(s.points for s in ev.series if s.code == code)


def test_price_times_volume_multi_period() -> None:
    drivers = [
        Driver("price", "Unit price", DriverKind.INPUT, values={"2026-01": D("100"), "2026-02": D("110")}),
        Driver("volume", "Units", DriverKind.INPUT, values={"2026-01": D("1000"), "2026-02": D("1200")}),
        Driver("revenue", "Revenue", DriverKind.FORMULA, formula="price * volume", account_code="4000"),
    ]
    ev = evaluate_model(drivers, ["2026-01", "2026-02"])
    assert _series(ev, "revenue") == [D("100000"), D("132000")]
    assert len(ev.account_lines) == 1
    assert ev.account_lines[0].account_code == "4000"
    assert ev.account_lines[0].total == D("232000")


def test_dependencies_resolved_out_of_order() -> None:
    # gross_profit depends on revenue and cogs, declared *before* them
    drivers = [
        Driver("gross_profit", "GP", DriverKind.FORMULA, formula="revenue - cogs"),
        Driver("cogs", "COGS", DriverKind.FORMULA, formula="revenue * 0.55", account_code="5000"),
        Driver("revenue", "Rev", DriverKind.INPUT, values={"2026-01": D("100000")}, account_code="4000"),
    ]
    ev = evaluate_model(drivers, ["2026-01"])
    assert _series(ev, "cogs") == [D("55000.00")]
    assert _series(ev, "gross_profit") == [D("45000.00")]


def test_prev_growth_chain() -> None:
    # revenue compounds 10% off its own prior period; first period seeds from an input base
    drivers = [
        Driver("base", "Seed", DriverKind.INPUT, values={"2026-01": D("1000")}),
        Driver(
            "revenue",
            "Revenue",
            DriverKind.FORMULA,
            formula="base + prev(revenue) * 1.1",
        ),
    ]
    ev = evaluate_model(drivers, ["2026-01", "2026-02", "2026-03"])
    # p1: 1000 + 0*1.1 = 1000 ; p2: 0 + 1000*1.1 = 1100 ; p3: 0 + 1100*1.1 = 1210
    assert _series(ev, "revenue") == [D("1000.0"), D("1100.0"), D("1210.00")]


def test_account_aggregates_multiple_drivers() -> None:
    drivers = [
        Driver("salaries", "Salaries", DriverKind.INPUT, values={"2026-01": D("50000")}, account_code="6100"),
        Driver("bonus", "Bonus", DriverKind.INPUT, values={"2026-01": D("5000")}, account_code="6100"),
    ]
    ev = evaluate_model(drivers, ["2026-01"])
    assert len(ev.account_lines) == 1
    assert ev.account_lines[0].points == [D("55000")]


def test_cycle_detected() -> None:
    drivers = [
        Driver("a", "A", DriverKind.FORMULA, formula="b + 1"),
        Driver("b", "B", DriverKind.FORMULA, formula="a + 1"),
    ]
    with pytest.raises(DriverError, match="cyclic"):
        evaluate_model(drivers, ["2026-01"])


def test_unknown_reference_and_duplicate() -> None:
    with pytest.raises(DriverError, match="unknown driver"):
        evaluate_model([Driver("a", "A", DriverKind.FORMULA, formula="ghost * 2")], ["2026-01"])
    dupes = [
        Driver("x", "X", DriverKind.INPUT),
        Driver("x", "X2", DriverKind.INPUT),
    ]
    with pytest.raises(DriverError, match="duplicate"):
        evaluate_model(dupes, ["2026-01"])


# --- API -------------------------------------------------------------------

client = TestClient(app)


def test_api_evaluate_happy_path() -> None:
    r = client.post(
        "/api/drivers/evaluate",
        json={
            "periods": ["2026-01", "2026-02"],
            "drivers": [
                {"code": "price", "name": "Price", "kind": "INPUT", "values": {"2026-01": "100", "2026-02": "100"}},
                {"code": "volume", "name": "Vol", "kind": "INPUT", "values": {"2026-01": "1000", "2026-02": "1100"}},
                {"code": "revenue", "name": "Revenue", "kind": "FORMULA", "formula": "price * volume", "account_code": "4000"},
            ],
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    rev = next(s for s in body["series"] if s["code"] == "revenue")
    assert rev["points"] == [100000.0, 110000.0]  # JSON numbers, not strings
    assert body["account_lines"][0]["total"] == 210000.0


def test_api_bad_formula_returns_422() -> None:
    r = client.post(
        "/api/drivers/evaluate",
        json={
            "periods": ["2026-01"],
            "drivers": [{"code": "x", "name": "X", "kind": "FORMULA", "formula": "__import__('os')"}],
        },
    )
    assert r.status_code == 422
