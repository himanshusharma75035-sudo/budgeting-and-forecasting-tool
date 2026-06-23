"""Safe formula evaluation for driver-based models.

Driver formulas are small arithmetic expressions over other drivers — e.g.
``units_sold * unit_price`` or ``prev(revenue) * (1 + growth_rate)``. They are evaluated with a
**restricted AST walker, never** :func:`eval`: only numeric literals, references to other drivers,
arithmetic/comparison/boolean operators, conditional (`a if cond else b`) expressions, and a small
whitelist of functions (``min``, ``max``, ``abs``, ``round`` and the cross-period helper ``prev``)
are permitted. Anything else — attribute access, subscripts, comprehensions, lambdas, dunder
names, imports — raises :class:`FormulaError`. All arithmetic is exact via :class:`decimal.Decimal`.
"""

from __future__ import annotations

import ast
from collections.abc import Callable, Mapping
from decimal import ROUND_HALF_UP, Decimal, DivisionByZero, InvalidOperation

from app.domain.money import to_decimal

#: Name of the cross-period reference function, handled specially (its first argument is a driver
#: *code*, not a value, and it reads previously-computed periods rather than the current one).
PREV = "prev"

PrevFn = Callable[[str, int], Decimal]


class FormulaError(ValueError):
    """Raised when a formula is malformed, unsafe, or references an unknown driver."""


def _fn_min(*args: Decimal) -> Decimal:
    return min(args)


def _fn_max(*args: Decimal) -> Decimal:
    return max(args)


def _fn_abs(x: Decimal) -> Decimal:
    return abs(x)


def _fn_round(x: Decimal, ndigits: Decimal = Decimal(0)) -> Decimal:
    return x.quantize(Decimal(1).scaleb(-int(ndigits)), rounding=ROUND_HALF_UP)


#: Direct value functions. ``prev`` is intentionally absent — it is supplied per-period by the engine.
_SAFE_FUNCS: dict[str, Callable[..., Decimal]] = {
    "min": _fn_min,
    "max": _fn_max,
    "abs": _fn_abs,
    "round": _fn_round,
}

_ALLOWED_FUNC_NAMES = frozenset(_SAFE_FUNCS) | {PREV}


# --- reference extraction (for dependency ordering) ------------------------


def extract_references(expr: str) -> set[str]:
    """Return the driver codes a formula references **in the same period**.

    Names inside ``prev(...)``'s first argument are excluded (they are previous-period references,
    so ``prev(revenue) * 1.1`` is not a self-cycle), as are the whitelisted function names.
    """
    tree = _parse(expr)
    refs: set[str] = set()
    _collect_refs(tree.body, refs)
    return refs


def _collect_refs(node: ast.AST, refs: set[str]) -> None:
    if isinstance(node, ast.Call):
        func_name = node.func.id if isinstance(node.func, ast.Name) else None
        args = node.args[1:] if func_name == PREV else node.args
        for arg in args:
            _collect_refs(arg, refs)
        for kw in node.keywords:
            _collect_refs(kw.value, refs)
        return
    if isinstance(node, ast.Name):
        if node.id not in _ALLOWED_FUNC_NAMES:
            refs.add(node.id)
        return
    for child in ast.iter_child_nodes(node):
        _collect_refs(child, refs)


# --- evaluation ------------------------------------------------------------


def evaluate(expr: str, names: Mapping[str, Decimal], prev: PrevFn | None = None) -> Decimal | bool:
    """Evaluate ``expr`` against same-period driver values ``names`` (and optional ``prev``)."""
    return _eval(_parse(expr).body, names, prev)


def _parse(expr: str) -> ast.Expression:
    try:
        return ast.parse(expr, mode="eval")
    except (SyntaxError, ValueError) as e:
        raise FormulaError(f"invalid formula syntax: {expr!r}") from e


def _eval(node: ast.expr, names: Mapping[str, Decimal], prev: PrevFn | None) -> Decimal | bool:
    if isinstance(node, ast.Constant):
        if isinstance(node.value, bool):
            return node.value
        if isinstance(node.value, (int, float)):
            return to_decimal(node.value)
        raise FormulaError(f"unsupported literal: {node.value!r}")
    if isinstance(node, ast.Name):
        try:
            return names[node.id]
        except KeyError:
            raise FormulaError(f"unknown driver reference: {node.id!r}") from None
    if isinstance(node, ast.UnaryOp):
        return _unary(node, names, prev)
    if isinstance(node, ast.BinOp):
        return _binop(node.op, _num(_eval(node.left, names, prev)), _num(_eval(node.right, names, prev)))
    if isinstance(node, ast.BoolOp):
        vals = [_truth(_eval(v, names, prev)) for v in node.values]
        return all(vals) if isinstance(node.op, ast.And) else any(vals)
    if isinstance(node, ast.Compare):
        return _compare(node, names, prev)
    if isinstance(node, ast.IfExp):
        branch = node.body if _truth(_eval(node.test, names, prev)) else node.orelse
        return _eval(branch, names, prev)
    if isinstance(node, ast.Call):
        return _call(node, names, prev)
    raise FormulaError(f"unsupported expression element: {type(node).__name__}")


def _unary(node: ast.UnaryOp, names: Mapping[str, Decimal], prev: PrevFn | None) -> Decimal | bool:
    operand = _eval(node.operand, names, prev)
    if isinstance(node.op, ast.UAdd):
        return +_num(operand)
    if isinstance(node.op, ast.USub):
        return -_num(operand)
    if isinstance(node.op, ast.Not):
        return not _truth(operand)
    raise FormulaError(f"unsupported unary operator: {type(node.op).__name__}")


def _binop(op: ast.operator, left: Decimal, right: Decimal) -> Decimal:
    try:
        if isinstance(op, ast.Add):
            return left + right
        if isinstance(op, ast.Sub):
            return left - right
        if isinstance(op, ast.Mult):
            return left * right
        if isinstance(op, ast.Div):
            if right == 0:
                raise FormulaError("division by zero")
            return left / right
    except (DivisionByZero, InvalidOperation) as e:
        raise FormulaError(f"arithmetic error: {e}") from e
    raise FormulaError(f"unsupported operator: {type(op).__name__}")


def _compare(node: ast.Compare, names: Mapping[str, Decimal], prev: PrevFn | None) -> bool:
    left = _num(_eval(node.left, names, prev))
    for op, comparator in zip(node.ops, node.comparators, strict=True):
        right = _num(_eval(comparator, names, prev))
        if not _cmp(op, left, right):
            return False
        left = right
    return True


def _cmp(op: ast.cmpop, a: Decimal, b: Decimal) -> bool:
    if isinstance(op, ast.Lt):
        return a < b
    if isinstance(op, ast.LtE):
        return a <= b
    if isinstance(op, ast.Gt):
        return a > b
    if isinstance(op, ast.GtE):
        return a >= b
    if isinstance(op, ast.Eq):
        return a == b
    if isinstance(op, ast.NotEq):
        return a != b
    raise FormulaError(f"unsupported comparison: {type(op).__name__}")


def _call(node: ast.Call, names: Mapping[str, Decimal], prev: PrevFn | None) -> Decimal:
    if not isinstance(node.func, ast.Name):
        raise FormulaError("only direct calls to whitelisted functions are allowed")
    if node.keywords:
        raise FormulaError("keyword arguments are not supported in formulas")
    fname = node.func.id
    if fname == PREV:
        if prev is None:
            raise FormulaError("prev() is not available in this context")
        if not node.args or not isinstance(node.args[0], ast.Name):
            raise FormulaError("prev() requires a driver name as its first argument")
        offset = 1 if len(node.args) < 2 else int(_num(_eval(node.args[1], names, prev)))
        return prev(node.args[0].id, offset)
    if fname in _SAFE_FUNCS:
        args = [_num(_eval(a, names, prev)) for a in node.args]
        try:
            return _SAFE_FUNCS[fname](*args)
        except (TypeError, ValueError, InvalidOperation) as e:
            raise FormulaError(f"error in {fname}(): {e}") from e
    raise FormulaError(f"unknown function: {fname!r}")


def _num(value: Decimal | bool) -> Decimal:
    if isinstance(value, bool):
        return Decimal(1) if value else Decimal(0)
    return value


def _truth(value: Decimal | bool) -> bool:
    if isinstance(value, bool):
        return value
    return value != 0
