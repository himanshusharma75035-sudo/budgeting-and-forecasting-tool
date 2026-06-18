"""Shared enumerations and account-type metadata used across the domain and DB layers."""

from __future__ import annotations

from enum import Enum


class AccountType(str, Enum):
    REVENUE = "REVENUE"
    COGS = "COGS"
    OPEX = "OPEX"
    OTHER_INCOME = "OTHER_INCOME"
    OTHER_EXPENSE = "OTHER_EXPENSE"
    ASSET = "ASSET"
    LIABILITY = "LIABILITY"
    EQUITY = "EQUITY"


class StatementSection(str, Enum):
    PL = "PL"
    BS = "BS"


class NormalBalance(str, Enum):
    DEBIT = "DEBIT"
    CREDIT = "CREDIT"


class BalanceType(str, Enum):
    FLOW = "FLOW"  # P&L flows accumulate across a period
    BALANCE = "BALANCE"  # Balance-sheet point-in-time values


class Scenario(str, Enum):
    ACTUAL = "ACTUAL"
    BUDGET = "BUDGET"
    FORECAST = "FORECAST"


class BudgetMethod(str, Enum):
    INCREMENTAL = "INCREMENTAL"
    ACTIVITY_BASED = "ACTIVITY_BASED"
    VALUE_PROPOSITION = "VALUE_PROPOSITION"
    ZERO_BASED = "ZERO_BASED"


class VolumeMode(str, Enum):
    STATIC = "STATIC"
    FLEXIBLE = "FLEXIBLE"


class Cadence(str, Enum):
    PERIODIC = "PERIODIC"
    ROLLING = "ROLLING"


class BudgetStatus(str, Enum):
    DRAFT = "DRAFT"
    SUBMITTED = "SUBMITTED"
    APPROVED = "APPROVED"
    ARCHIVED = "ARCHIVED"


class VarianceKind(str, Enum):
    BUDGET_VS_ACTUAL = "BUDGET_VS_ACTUAL"
    FORECAST_VS_ACTUAL = "FORECAST_VS_ACTUAL"
    FLEX_BUDGET = "FLEX_BUDGET"
    SALES_VOLUME = "SALES_VOLUME"
    SALES_PRICE = "SALES_PRICE"
    SALES_MIX = "SALES_MIX"
    SALES_QTY = "SALES_QTY"
    MAT_PRICE = "MAT_PRICE"
    MAT_QTY = "MAT_QTY"
    LABOR_RATE = "LABOR_RATE"
    LABOR_EFFICIENCY = "LABOR_EFFICIENCY"
    VOH_SPENDING = "VOH_SPENDING"
    VOH_EFFICIENCY = "VOH_EFFICIENCY"
    FOH_SPENDING = "FOH_SPENDING"
    FOH_VOLUME = "FOH_VOLUME"


class VarianceStatus(str, Enum):
    FAVORABLE = "FAVORABLE"
    UNFAVORABLE = "UNFAVORABLE"
    NEUTRAL = "NEUTRAL"


# --- account-type metadata -------------------------------------------------

#: Accounts whose increase is recorded on the debit side.
DEBIT_NORMAL = {
    AccountType.ASSET,
    AccountType.COGS,
    AccountType.OPEX,
    AccountType.OTHER_EXPENSE,
}

#: P&L sign factor so that ``Net Income = sum(amount * sign_factor)``.
#: Revenue/income contribute +1; cost/expense contribute -1.
SIGN_FACTOR: dict[AccountType, int] = {
    AccountType.REVENUE: 1,
    AccountType.OTHER_INCOME: 1,
    AccountType.COGS: -1,
    AccountType.OPEX: -1,
    AccountType.OTHER_EXPENSE: -1,
    # Balance-sheet types are not part of the P&L sign convention.
    AccountType.ASSET: 1,
    AccountType.LIABILITY: 1,
    AccountType.EQUITY: 1,
}

#: True for cost/expense P&L accounts (drives favorable/unfavorable interpretation).
COST_TYPES = {AccountType.COGS, AccountType.OPEX, AccountType.OTHER_EXPENSE}


def normal_balance(account_type: AccountType) -> NormalBalance:
    return NormalBalance.DEBIT if account_type in DEBIT_NORMAL else NormalBalance.CREDIT


def sign_factor(account_type: AccountType) -> int:
    return SIGN_FACTOR[account_type]


def is_cost(account_type: AccountType) -> bool:
    return account_type in COST_TYPES
