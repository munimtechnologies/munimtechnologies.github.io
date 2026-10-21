# SPDX-License-Identifier: Apache-2.0
# Part of MV2's eval-reliability audits (Munim, Inc.). Made with AI.
"""Exact, sandboxed arithmetic for auditing GSM8K's <<expr=result>> annotations.

The evaluator parses an expression with Python's ``ast`` and walks a strict
whitelist of + - * / and unary +/- over exact ``Fraction`` values. Anything
else (names, calls, power, modulo, attributes, ...) raises ``UnparseableExpr``
so a census can count it rather than crash. Division is exact (rationals), so
a terminating annotation like 48/2=24 is judged against the true value, and a
non-terminating one like 2/3=0.67 is judged as a rounding, not an error.
"""

import ast
import re
from decimal import Decimal, ROUND_HALF_UP
from fractions import Fraction

_ALLOWED_BINOPS = (ast.Add, ast.Sub, ast.Mult, ast.Div)
_ALLOWED_UNARY = (ast.UAdd, ast.USub)

# A plain decimal number, optionally signed, with an optional single '.'.
_NUM_RE = re.compile(r"^[+-]?(?:\d+\.?\d*|\.\d+)$")


class UnparseableExpr(Exception):
    """Raised when an expression/result is outside the arithmetic whitelist."""


def _eval_node(node):
    if isinstance(node, ast.Expression):
        return _eval_node(node.body)
    if isinstance(node, ast.BinOp):
        if not isinstance(node.op, _ALLOWED_BINOPS):
            raise UnparseableExpr("binop:" + type(node.op).__name__)
        left = _eval_node(node.left)
        right = _eval_node(node.right)
        if isinstance(node.op, ast.Add):
            return left + right
        if isinstance(node.op, ast.Sub):
            return left - right
        if isinstance(node.op, ast.Mult):
            return left * right
        # Div
        if right == 0:
            raise UnparseableExpr("div0")
        return left / right
    if isinstance(node, ast.UnaryOp):
        if not isinstance(node.op, _ALLOWED_UNARY):
            raise UnparseableExpr("unary:" + type(node.op).__name__)
        operand = _eval_node(node.operand)
        return operand if isinstance(node.op, ast.UAdd) else -operand
    if isinstance(node, ast.Constant):
        # Reject bools (a subclass of int) and non-numbers.
        if isinstance(node.value, bool) or not isinstance(node.value, (int, float)):
            raise UnparseableExpr("const")
        # str() gives the short decimal repr, so 0.1 -> Fraction(1, 10) exactly.
        return Fraction(str(node.value))
    raise UnparseableExpr("node:" + type(node).__name__)


def safe_eval(expr):
    """Evaluate an arithmetic expression to an exact Fraction, or raise."""
    cleaned = expr.replace(",", "").strip()  # drop thousands separators
    if not cleaned:
        raise UnparseableExpr("empty")
    try:
        tree = ast.parse(cleaned, mode="eval")
    except (SyntaxError, ValueError):
        raise UnparseableExpr("syntax")
    return _eval_node(tree)


def decimals_in(s):
    """Count decimal places shown in a numeric string."""
    s = s.strip()
    if "." in s:
        return len(s.split(".", 1)[1])
    return 0


def parse_number(s):
    """Parse a plain decimal number to (Fraction, shown_decimal_places)."""
    cleaned = s.replace(",", "").strip()
    if not _NUM_RE.match(cleaned):
        raise UnparseableExpr("num:" + cleaned)
    return Fraction(cleaned), decimals_in(cleaned)


def _round_to(value, places):
    """Round an exact Fraction to ``places`` decimals (half-up) as a Fraction."""
    dec = Decimal(value.numerator) / Decimal(value.denominator)
    quantum = Decimal(1).scaleb(-places)
    return Fraction(dec.quantize(quantum, rounding=ROUND_HALF_UP))


def classify_annotation(expr, result_str):
    """Classify one <<expr=result>> annotation.

    Returns one of: 'match' (exact), 'rounded' (equals result once the true
    value is rounded to the places shown), 'mismatch' (neither), or
    'unparseable_expr' / 'unparseable_result' when a side is outside the
    whitelist. 'rounded' is reported separately and is NOT counted as an error.
    """
    try:
        value = safe_eval(expr)
    except UnparseableExpr:
        return "unparseable_expr"
    try:
        stated, places = parse_number(result_str)
    except UnparseableExpr:
        return "unparseable_result"
    if value == stated:
        return "match"
    if _round_to(value, places) == stated:
        return "rounded"
    return "mismatch"


_ANNOT_RE = re.compile(r"<<(.+?)=(.+?)>>")
_FINAL_RE = re.compile(r"####\s*(.+)")


def find_annotations(answer_text):
    """Return a list of (expr, result_str) for every annotation, in order."""
    return _ANNOT_RE.findall(answer_text)


def solution_consistency(answer_text):
    """Check whether the final '#### answer' equals the last annotation's result.

    Returns a dict with has_annotation / has_final / final_matches_last
    (None when not applicable or a side is unparseable).
    """
    annots = find_annotations(answer_text)
    if not annots:
        return {"has_annotation": False, "has_final": None, "final_matches_last": None}
    last_result = annots[-1][1]
    m = _FINAL_RE.search(answer_text)
    if not m:
        return {"has_annotation": True, "has_final": False, "final_matches_last": None}
    try:
        final_val, _ = parse_number(m.group(1))
        last_val, _ = parse_number(last_result)
    except UnparseableExpr:
        return {"has_annotation": True, "has_final": True, "final_matches_last": None}
    return {"has_annotation": True, "has_final": True, "final_matches_last": final_val == last_val}
