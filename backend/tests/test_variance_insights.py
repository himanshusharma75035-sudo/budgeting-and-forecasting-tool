"""Tests for variance insights, narrative composition, the AI-off path, and the API."""

from __future__ import annotations

import io
from decimal import Decimal

from fastapi.testclient import TestClient

from app.db.session import init_db
from app.domain.enums import VarianceStatus
from app.domain.variance import VarianceItem, build_insights, compose_narrative
from app.main import app
from app.services.ai import ai_available, enrich_narrative

D = Decimal

init_db()
client = TestClient(app)


def _items() -> list[VarianceItem]:
    return [
        VarianceItem("4000", "Revenue", "Revenue from operations", D("-250000"), D("750000"), D("1000000"), True),
        VarianceItem("5000", "Materials", "Cost of materials", D("150000"), D("450000"), D("600000"), True),
        VarianceItem("6000", "Other expenses", "Other expenses", D("50000"), D("250000"), D("300000"), False),
    ]


# --- engine ----------------------------------------------------------------


def test_build_insights_nets_and_ranks() -> None:
    ins = build_insights(_items())
    assert ins.net_favorable == D("-50000")  # -250000 + 150000 + 50000
    assert ins.status == VarianceStatus.UNFAVORABLE
    assert ins.favorable_total == D("200000")
    assert ins.unfavorable_total == D("-250000")
    assert ins.top_unfavorable[0].label == "Revenue"
    assert ins.top_favorable[0].label == "Materials"  # bigger favourable than Other expenses
    # material drivers ranked by magnitude (only the two flagged material)
    assert [d.label for d in ins.material] == ["Revenue", "Materials"]


def test_by_category_aggregates() -> None:
    items = [
        VarianceItem("6100", "Salaries", "Employee benefits", D("10000"), D("90000"), D("100000"), False),
        VarianceItem("6200", "Bonus", "Employee benefits", D("5000"), D("45000"), D("50000"), False),
    ]
    ins = build_insights(items)
    employee = next(d for d in ins.by_category if d.category == "Employee benefits")
    assert employee.favorable_variance == D("15000")
    assert employee.actual == D("135000")


def test_neutral_when_balanced() -> None:
    items = [
        VarianceItem("4000", "Revenue", "Rev", D("10000"), D("110000"), D("100000"), False),
        VarianceItem("5000", "COGS", "COGS", D("-10000"), D("60000"), D("50000"), False),
    ]
    ins = build_insights(items)
    assert ins.net_favorable == D("0")
    assert ins.status == VarianceStatus.NEUTRAL


def test_compose_narrative_text() -> None:
    text = compose_narrative(build_insights(_items()), lambda d: f"₹{d}")
    assert "unfavourable" in text
    assert "Biggest drags" in text
    assert "Largest offsets" in text
    assert "materiality threshold" in text


# --- AI is off by default --------------------------------------------------


def test_ai_disabled_by_default() -> None:
    assert ai_available() is False
    assert enrich_narrative("any commentary") is None


# --- API -------------------------------------------------------------------


def _make_account(code: str, name: str, atype: str) -> None:
    client.post("/api/accounts", json={"account_code": code, "account_name": name, "account_type": atype})


def test_api_insights_end_to_end() -> None:
    _make_account("4100", "Sales", "REVENUE")
    _make_account("6200", "Marketing", "OPEX")
    period = "2027-06"  # isolated period so this test is independent of other fixtures
    header = "account_code,entity_code,department_code,project_code,region_code,currency,2027-06\n"
    actual = header + "4100,ALL,UNALLOC,NONE,ALL,INR,120000\n6200,ALL,UNALLOC,NONE,ALL,INR,30000\n"
    budget = header + "4100,ALL,UNALLOC,NONE,ALL,INR,100000\n6200,ALL,UNALLOC,NONE,ALL,INR,25000\n"
    client.post("/api/uploads?scenario=ACTUAL", files={"file": ("a.csv", io.BytesIO(actual.encode()), "text/csv")})
    client.post("/api/uploads?scenario=BUDGET", files={"file": ("b.csv", io.BytesIO(budget.encode()), "text/csv")})

    r = client.post(
        "/api/variance/insights",
        json={"base_scenario": "ACTUAL", "compare_scenario": "BUDGET", "period_from": period, "period_to": period},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    # revenue +20000 favourable, opex -5000 unfavourable -> net +15000 favourable
    assert body["status"] == "FAVORABLE"
    assert body["net_favorable"] == 15000.0
    assert body["ai_generated"] is False
    assert "favourable" in body["narrative"]
    assert body["top_favorable"][0]["label"] == "Sales"
