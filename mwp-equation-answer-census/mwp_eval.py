# Safe equation evaluators for the mwp-equation-answer-census audit.
#
# Two annotation formats appear in the public math-word-problem (MWP) datasets
# this census covers:
#   * SVAMP (arkilpatel/SVAMP, SVAMP.json): the annotated "Equation" is an INFIX
#     arithmetic expression over literal numbers, e.g. "( 76.0 - 25.0 )".
#   * ASDiv-A and MAWPS (the Patel et al. CV release): the annotated "Equation"
#     is in PREFIX (Polish) notation over number tokens, e.g. "- number0 number1",
#     with a space-separated "Numbers" column giving number0, number1, ....
#
# Neither path uses Python `eval`. Infix is parsed with `ast` and walked with a
# whitelist of numeric binary/unary ops only; prefix is parsed with a small
# stack machine. Nothing is run against any live system.
#
# Audit code by AI agents working in MV2's name (Munim, Inc.). Apache-2.0.

import ast
import operator

_BIN = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
}
_UNARY = {
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}


def eval_infix(expr):
    """Safely evaluate an infix arithmetic expression. Raises ValueError on
    anything outside +, -, *, / over numeric literals."""
    node = ast.parse(expr, mode="eval").body
    return _ev(node)


def _ev(node):
    if isinstance(node, ast.Constant):
        if isinstance(node.value, bool) or not isinstance(node.value, (int, float)):
            raise ValueError("non-numeric constant")
        return float(node.value)
    # Python <3.8 compatibility; harmless on 3.12.
    if isinstance(node, getattr(ast, "Num", ())):  # pragma: no cover
        return float(node.n)
    if isinstance(node, ast.BinOp) and type(node.op) in _BIN:
        return _BIN[type(node.op)](_ev(node.left), _ev(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY:
        return _UNARY[type(node.op)](_ev(node.operand))
    raise ValueError("disallowed node: " + type(node).__name__)


def eval_prefix(tokens, numbers):
    """Evaluate a prefix (Polish) expression. `tokens` is a list like
    ['-', 'number0', 'number1']; `numbers` maps numberK -> numbers[K]. Literal
    numeric tokens are allowed too. Raises on malformed input."""
    stack = []
    for tok in reversed(tokens):
        if tok in ("+", "-", "*", "/"):
            if len(stack) < 2:
                raise ValueError("prefix underflow")
            a = stack.pop()
            b = stack.pop()
            stack.append(_apply(tok, a, b))
        else:
            stack.append(_operand(tok, numbers))
    if len(stack) != 1:
        raise ValueError("prefix leftover")
    return stack[0]


def _operand(tok, numbers):
    if tok.startswith("number"):
        idx = int(tok[len("number"):])
        return float(numbers[idx])
    return float(tok)


def _apply(op, a, b):
    if op == "+":
        return a + b
    if op == "-":
        return a - b
    if op == "*":
        return a * b
    if op == "/":
        return a / b
    raise ValueError("bad op " + op)


def is_close(a, b, tol=1e-3):
    """True if a and b agree to absolute OR relative tolerance tol."""
    if a is None or b is None:
        return False
    if abs(a - b) <= tol:
        return True
    denom = max(abs(a), abs(b), 1.0)
    return abs(a - b) / denom <= tol


def classify(notation, equation, numbers, answer, tol=1e-3):
    """Return (verdict, computed_value). verdict is one of:
    'match'       -- annotated equation evaluates to the annotated answer;
    'mismatch'    -- it evaluates to a different number;
    'unevaluable' -- the equation could not be evaluated (parse error, bad
                     token, division by zero, missing number slot)."""
    try:
        if notation == "infix":
            val = eval_infix(equation)
        elif notation == "prefix":
            val = eval_prefix(equation.split(), numbers)
        else:
            raise ValueError("unknown notation " + str(notation))
    except Exception:
        return "unevaluable", None
    try:
        ans = float(answer)
    except (TypeError, ValueError):
        return "unevaluable", val
    return ("match" if is_close(val, ans, tol) else "mismatch"), val
