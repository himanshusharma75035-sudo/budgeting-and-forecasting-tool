"""End-to-end API smoke test exercising the wired routes via FastAPI's TestClient."""

from __future__ import annotations

import io

from fastapi.testclient import TestClient

from app.db.session import init_db
from app.main import app

init_db()  # TestClient(app) without a context manager doesn't fire the lifespan startup
client = TestClient(app)


def _make_account(code: str, name: str, atype: str) -> None:
    r = client.post("/api/accounts", json={
        "account_code": code, "account_name": name, "account_type": atype,
    })
    assert r.status_code in (201, 409), r.text


def test_health() -> None:
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_accounts_crud() -> None:
    _make_account("4000", "Product Revenue", "REVENUE")
    _make_account("6100", "Marketing", "OPEX")
    rows = client.get("/api/accounts").json()
    codes = {a["account_code"] for a in rows}
    assert {"4000", "6100"} <= codes
    rev = next(a for a in rows if a["account_code"] == "4000")
    assert rev["normal_balance"] == "CREDIT" and rev["sign_factor"] == 1


def test_incremental_budget_run() -> None:
    r = client.post("/api/budgets/run", json={
        "method": "INCREMENTAL",
        "version_name": "FY26 Plan",
        "fiscal_year": 2026,
        "incremental_lines": [
            {"account_code": "6100", "prior_actual": "200000", "growth_pct": "0.08", "one_off": "15000"}
        ],
    })
    assert r.status_code == 200, r.text
    body = r.json()
    assert float(body["total"]) == 231000.0
    assert body["budget_version_id"] is not None


def test_value_proposition_budget_run() -> None:
    r = client.post("/api/budgets/run", json={
        "method": "VALUE_PROPOSITION",
        "version_name": "VP test",
        "fiscal_year": 2026,
        "cap": "100000",
        "initiatives": [
            {"name": "A", "cost": "40000", "value_score": "90"},
            {"name": "B", "cost": "30000", "value_score": "75"},
            {"name": "C", "cost": "50000", "value_score": "60"},
            {"name": "D", "cost": "20000", "value_score": "50"},
        ],
    })
    assert r.status_code == 200, r.text
    body = r.json()
    funded = {line["name"] for line in body["lines"]}
    assert funded == {"A", "B", "D"}
    assert float(body["total"]) == 90000.0


def test_forecast_inline_history() -> None:
    history = [100 + 3 * i for i in range(36)]  # clean linear trend
    r = client.post("/api/forecasts/run", json={
        "account_code": "4000", "history": history, "horizon": 6, "levels": [80, 95],
    })
    assert r.status_code == 200, r.text
    body = r.json()
    assert len(body["point"]) == 6
    assert set(body["lower"].keys()) == {"80", "95"}
    assert body["selected_model"]
    assert len(body["scoreboard"]) >= 1


def test_upload_and_variance_flow() -> None:
    # upload ACTUALS for 4000 (revenue) and 6100 (opex)
    wide = (
        "account_code,entity_code,department_code,project_code,region_code,currency,2026-01,2026-02\n"
        "4000,ALL,UNALLOC,NONE,ALL,USD,120000,125000\n"
        "6100,ALL,UNALLOC,NONE,ALL,USD,18000,19000\n"
    )
    files = {"file": ("actuals.csv", io.BytesIO(wide.encode()), "text/csv")}
    r = client.post("/api/uploads?scenario=ACTUAL", files=files)
    assert r.status_code == 200, r.text
    rep = r.json()
    assert rep["layout"] == "WIDE"
    assert rep["inserted"] == 4 and rep["rows_rejected"] == 0

    # upload a BUDGET to compare against
    budget = (
        "account_code,entity_code,department_code,project_code,region_code,currency,2026-01,2026-02\n"
        "4000,ALL,UNALLOC,NONE,ALL,USD,130000,130000\n"
        "6100,ALL,UNALLOC,NONE,ALL,USD,17000,17000\n"
    )
    files = {"file": ("budget.csv", io.BytesIO(budget.encode()), "text/csv")}
    r = client.post("/api/uploads?scenario=BUDGET", files=files)
    assert r.status_code == 200, r.text

    r = client.post("/api/variance/compute", json={
        "base_scenario": "ACTUAL", "compare_scenario": "BUDGET",
        "period_from": "2026-01", "period_to": "2026-02",
    })
    assert r.status_code == 200, r.text
    rows = r.json()
    # revenue 4000 Jan: actual 120000 vs budget 130000 -> under -> UNFAVORABLE for revenue
    rev_jan = next(x for x in rows if x["account_code"] == "4000" and x["period"] == "2026-01")
    assert float(rev_jan["variance"]) == -10000.0
    assert rev_jan["status"] == "UNFAVORABLE"
    # opex 6100 Jan: actual 18000 vs budget 17000 -> over -> UNFAVORABLE for cost
    opex_jan = next(x for x in rows if x["account_code"] == "6100" and x["period"] == "2026-01")
    assert float(opex_jan["variance"]) == 1000.0
    assert opex_jan["status"] == "UNFAVORABLE"

    # bridge reconciles: start + sum(deltas) == end
    r = client.post("/api/variance/bridge", json={
        "base_scenario": "ACTUAL", "compare_scenario": "BUDGET",
    })
    assert r.status_code == 200, r.text
    b = r.json()
    total = float(b["start"]) + sum(float(s["delta"]) for s in b["steps"])
    assert abs(total - float(b["end"])) < 0.01
