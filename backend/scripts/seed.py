"""Seed a realistic Indian (Schedule III, Companies Act 2013) demo workspace.

Creates a comprehensive chart of accounts, dimensions, ~3 years of monthly ACTUALS with
trend + festive-season seasonality, and a BUDGET version for the latest fiscal year so the
variance and forecasting features have rich data. All figures are synthetic. Currency = INR,
fiscal year = April–March.

Run:  python scripts/seed.py
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlmodel import Session, select  # noqa: E402

from app.config import settings  # noqa: E402
from app.db.models import (  # noqa: E402
    Account,
    BudgetVersion,
    DimDepartment,
    DimEntity,
    DimProject,
    DimRegion,
    Entry,
    Period,
)
from app.db.session import engine, init_db  # noqa: E402
from app.domain.enums import (  # noqa: E402
    AccountType,
    BalanceType,
    BudgetMethod,
    Cadence,
    Scenario,
    VolumeMode,
    normal_balance,
    sign_factor,
)
from app.domain.money import to_minor  # noqa: E402
from app.domain.periods import (  # noqa: E402
    add_months,
    fiscal_attrs,
    make_period_key,
    month_bounds,
    month_name,
    period_range,
    split_period_key,
)

R, OI, COGS, OPEX, OE = (
    AccountType.REVENUE,
    AccountType.OTHER_INCOME,
    AccountType.COGS,
    AccountType.OPEX,
    AccountType.OTHER_EXPENSE,
)
ASSET, LIAB, EQ = AccountType.ASSET, AccountType.LIABILITY, AccountType.EQUITY

# code, name, type, category, monthly_base (None = balance-sheet account, no monthly flow)
ACCOUNTS: list[tuple[str, str, AccountType, str, int | None]] = [
    ("4000", "Revenue from Operations - Products", R, "Revenue from operations", 38_000_000),
    ("4010", "Revenue from Operations - Services", R, "Revenue from operations", 6_500_000),
    ("4090", "Other Operating Revenue", R, "Revenue from operations", 1_200_000),
    ("4100", "Interest Income", OI, "Other income", 450_000),
    ("4110", "Other Non-operating Income", OI, "Other income", 300_000),
    ("5000", "Cost of Materials Consumed", COGS, "Cost of materials consumed", 19_000_000),
    ("5010", "Purchases of Stock-in-Trade", COGS, "Purchases of stock-in-trade", 3_200_000),
    ("5020", "Changes in Inventories", COGS, "Changes in inventories", 700_000),
    ("6000", "Salaries & Wages", OPEX, "Employee benefits expense", 5_400_000),
    ("6010", "Contribution to PF & ESI", OPEX, "Employee benefits expense", 620_000),
    ("6020", "Staff Welfare Expenses", OPEX, "Employee benefits expense", 280_000),
    ("6100", "Power & Fuel", OPEX, "Other expenses", 1_750_000),
    ("6110", "Rent", OPEX, "Other expenses", 950_000),
    ("6120", "Repairs & Maintenance - Plant", OPEX, "Other expenses", 540_000),
    ("6130", "Repairs & Maintenance - Building", OPEX, "Other expenses", 220_000),
    ("6140", "Insurance", OPEX, "Other expenses", 180_000),
    ("6150", "Rates & Taxes", OPEX, "Other expenses", 240_000),
    ("6160", "Travelling & Conveyance", OPEX, "Other expenses", 410_000),
    ("6170", "Legal & Professional Fees", OPEX, "Other expenses", 360_000),
    ("6180", "Payment to Auditors", OPEX, "Other expenses", 90_000),
    ("6190", "Advertisement & Sales Promotion", OPEX, "Other expenses", 1_300_000),
    ("6200", "Freight & Forwarding", OPEX, "Other expenses", 880_000),
    ("6210", "Communication", OPEX, "Other expenses", 130_000),
    ("6220", "Miscellaneous Expenses", OPEX, "Other expenses", 320_000),
    ("7000", "Finance Costs - Interest", OE, "Finance costs", 1_250_000),
    ("7010", "Other Borrowing Costs", OE, "Finance costs", 180_000),
    ("7100", "Depreciation & Amortization", OE, "Depreciation & amortization", 2_100_000),
    ("8000", "Current Tax", OE, "Tax expense", 1_400_000),
    ("8010", "Deferred Tax", OE, "Tax expense", 150_000),
    # Balance sheet (no monthly flow)
    ("3000", "Share Capital", EQ, "Shareholders' funds", None),
    ("3100", "Reserves & Surplus", EQ, "Shareholders' funds", None),
    ("2000", "Long-term Borrowings", LIAB, "Non-current liabilities", None),
    ("2100", "Trade Payables", LIAB, "Current liabilities", None),
    ("2200", "Short-term Borrowings", LIAB, "Current liabilities", None),
    ("2300", "Other Current Liabilities", LIAB, "Current liabilities", None),
    ("2400", "Short-term Provisions", LIAB, "Current liabilities", None),
    ("1000", "Property, Plant & Equipment", ASSET, "Non-current assets", None),
    ("1100", "Intangible Assets", ASSET, "Non-current assets", None),
    ("1200", "Inventories", ASSET, "Current assets", None),
    ("1300", "Trade Receivables", ASSET, "Current assets", None),
    ("1400", "Cash & Bank Balances", ASSET, "Current assets", None),
    ("1500", "Short-term Loans & Advances", ASSET, "Current assets", None),
]

# account code -> department id
DEPT_OF: dict[str, int] = {
    "4000": 2, "4010": 2, "4090": 2, "4100": 5, "4110": 5,
    "5000": 1, "5010": 1, "5020": 1,
    "6000": 1, "6010": 4, "6020": 4,
    "6100": 1, "6110": 4, "6120": 1, "6130": 4, "6140": 4, "6150": 4,
    "6160": 2, "6170": 5, "6180": 5, "6190": 2, "6200": 6, "6210": 4, "6220": 4,
    "7000": 5, "7010": 5, "7100": 1, "8000": 5, "8010": 5,
}

ENTITY_ID = 1
START = make_period_key(2023, 4)  # Apr 2023
N_MONTHS = 36  # Apr 2023 .. Mar 2026 (FY24, FY25, FY26)


def _seasonal_actual(base: int, i: int) -> float:
    """Trend + festive-season (peak ~Oct) seasonality + per-account phase noise."""
    trend = base * (1 + 0.005 * i)
    cal_month = ((3 + i) % 12) + 1  # calendar month of index i (start = April)
    season = 1 + 0.12 * math.sin((2 * math.pi * (cal_month - 1)) / 12 - 1.0)
    noise = 1 + 0.03 * math.sin(i * 1.9 + (base % 7))
    return trend * season * noise


def _budget_growth(code: str) -> float:
    return 1.05 + (sum(ord(c) for c in code) % 8) / 100.0  # 1.05 .. 1.12


def _ensure_dimensions(s: Session) -> None:
    rows: list[tuple[type, str, list[tuple[int, str, str]]]] = [
        (DimEntity, "entity_id", [(1, "DEMO", "Demo Manufacturing Pvt Ltd")]),
        (DimDepartment, "department_id", [
            (1, "MFG", "Manufacturing"), (2, "SALES", "Sales & Marketing"),
            (3, "RND", "Research & Development"), (4, "ADMIN", "Administration"),
            (5, "FIN", "Finance"), (6, "LOG", "Logistics"),
        ]),
        (DimRegion, "region_id", [
            (1, "NORTH", "North India"), (2, "SOUTH", "South India"),
            (3, "EAST", "East India"), (4, "WEST", "West India"),
        ]),
        (DimProject, "project_id", []),
    ]
    for model, pk, members in rows:
        for mid, code, name in members:
            if s.get(model, mid) is None:
                obj = model(code=code, name=name)
                setattr(obj, pk, mid)
                s.add(obj)
    s.commit()


def _ensure_accounts(s: Session) -> None:
    for idx, (code, name, atype, category, _base) in enumerate(ACCOUNTS):
        if s.exec(select(Account).where(Account.account_code == code)).first():
            continue
        is_pl = atype not in (ASSET, LIAB, EQ)
        s.add(
            Account(
                account_code=code,
                account_name=name,
                account_type=atype,
                account_category=category,
                statement_section="PL" if is_pl else "BS",  # type: ignore[arg-type]
                balance_type=BalanceType.FLOW if is_pl else BalanceType.BALANCE,
                normal_balance=normal_balance(atype),
                sign_factor=sign_factor(atype),
                is_postable=True,
                sort_order=idx,
            )
        )
    s.commit()


def _ensure_periods(s: Session, start_key: int, end_key: int) -> None:
    for key in period_range(start_key, end_key):
        if s.get(Period, key):
            continue
        year, month = split_period_key(key)
        fa = fiscal_attrs(key, settings.fiscal_year_start_month)
        p_start, p_end = month_bounds(key)
        s.add(
            Period(
                period_key=key, year=year, month_num=month, month_name=month_name(key),
                quarter=fa["quarter"], period_start_date=p_start, period_end_date=p_end,
                fiscal_year=fa["fiscal_year"], fiscal_quarter=fa["fiscal_quarter"],
                fiscal_period_num=fa["fiscal_period_num"],
            )
        )
    s.commit()


def _seed_actuals(s: Session, acct_ids: dict[str, int]) -> int:
    if s.exec(select(Entry).where(Entry.scenario == Scenario.ACTUAL)).first():
        return 0
    n = 0
    for code, _name, _t, _cat, base in ACCOUNTS:
        if base is None:
            continue
        dept = DEPT_OF.get(code, 4)
        for i in range(N_MONTHS):
            key = add_months(START, i)
            s.add(
                Entry(
                    account_id=acct_ids[code], period_key=key, entity_id=ENTITY_ID,
                    department_id=dept, scenario=Scenario.ACTUAL,
                    amount_minor=to_minor(_seasonal_actual(base, i)),
                    currency=settings.base_currency, source="seed",
                )
            )
            n += 1
    s.commit()
    return n


def _seed_budget(s: Session, acct_ids: dict[str, int]) -> int:
    """FY2025-26 budget = prior-year actual x per-account growth (incremental method)."""
    if s.exec(select(BudgetVersion)).first():
        return 0
    version = BudgetVersion(
        version_name="FY26 Operating Plan", fiscal_year=2026, method=BudgetMethod.INCREMENTAL,
        volume_mode=VolumeMode.STATIC, cadence=Cadence.PERIODIC, status="APPROVED",  # type: ignore[arg-type]
        is_active=True, created_by="seed",
    )
    s.add(version)
    s.commit()
    s.refresh(version)

    n = 0
    fy26_indices = range(24, 36)  # Apr 2025 .. Mar 2026
    for code, _name, _t, _cat, base in ACCOUNTS:
        if base is None:
            continue
        dept = DEPT_OF.get(code, 4)
        gf = _budget_growth(code)
        for i in fy26_indices:
            key = add_months(START, i)
            budget_val = _seasonal_actual(base, i - 12) * gf  # prior-year actual x growth
            s.add(
                Entry(
                    account_id=acct_ids[code], period_key=key, entity_id=ENTITY_ID,
                    department_id=dept, scenario=Scenario.BUDGET,
                    budget_version_id=version.budget_version_id,
                    amount_minor=to_minor(budget_val),
                    currency=settings.base_currency, source="seed",
                )
            )
            n += 1
    s.commit()
    return n


def main() -> None:
    init_db()
    end = add_months(START, N_MONTHS - 1)
    with Session(engine) as s:
        _ensure_dimensions(s)
        _ensure_accounts(s)
        _ensure_periods(s, START, add_months(end, 12))  # + a year of future periods
        acct_ids = {a.account_code: a.account_id for a in s.exec(select(Account)).all()}
        n_actual = _seed_actuals(s, acct_ids)  # type: ignore[arg-type]
        n_budget = _seed_budget(s, acct_ids)  # type: ignore[arg-type]
    print(
        f"Seeded {len(ACCOUNTS)} accounts, {n_actual} actual + {n_budget} budget entries "
        f"(INR, FY Apr-Mar) into {settings.database_url}"
    )


if __name__ == "__main__":
    main()
