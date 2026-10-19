"""MathQA annotated_formula consistency audit (core logic).

The MathQA dataset (Amini et al., 2019; allenai/math_qa) ships two program
representations per problem: `annotated_formula` (a nested, human-readable
expression with LITERAL numbers, e.g. `power(5, 4)`) and `linear_formula` (a
flattened program using `n0,n1,...` references to numbers extracted from the
problem text, e.g. `power(n1,n0)|`).

Because `annotated_formula` embeds literal numbers, it can be evaluated with NO
reference to the problem text at all: there is no number-extraction step, and so
no number-extraction error. This module evaluates `annotated_formula` directly
and checks whether it equals the labelled correct option.

Everything is standard library only. Exact values are carried as
`fractions.Fraction`; only operations/constants that are genuinely irrational
(sqrt, const_pi, ...) fall back to float. A value is `exact=True` iff it was
produced entirely by rational-preserving operations over exact inputs.

MAGNITUDE CAP (added v4). v2 crashed on `float(10^400)` (OverflowError); v3 fixed
the crash by comparing over-range values as exact rationals, but then TIMED OUT
(exit 124, 3600 s): a nested power tower or a large `factorial`/`choose` builds a
multi-million-bit integer whose very CONSTRUCTION (and later str()/arithmetic)
hangs, even though no float is ever taken. v4 caps the bit-length of any exact
value at `MAX_VALUE_BITS`. An operation whose result would exceed the cap raises
`EvalError`, so the problem is reported as "unevaluable (value too large to
check)" instead of hanging. The cap (65536 bits ~= 19,728 decimal digits) is
astronomically larger than any real MathQA answer option, so it never turns a
genuinely checkable formula into "unevaluable": only runaway towers, which could
not match a small option anyway, are set aside.

This file is import-only; `job.py` drives it over the real dataset.
"""

from __future__ import annotations

import math
import re
from fractions import Fraction


class EvalError(Exception):
    """Raised when a formula cannot be evaluated with the supported op/const set."""


# --- magnitude cap ----------------------------------------------------------
# Any exact value whose numerator or denominator exceeds this many bits is
# treated as "too large to check" and raises EvalError (classified unevaluable).
MAX_VALUE_BITS = 1 << 16  # 65536 bits ~= 19,728 decimal digits
_LN2 = math.log(2)


def _bits(fr):
    """Approximate bit-length of a Fraction's magnitude (max of num/den)."""
    return max(fr.numerator.bit_length(), fr.denominator.bit_length())


def _guard(fr):
    """Return fr unchanged, or raise if its magnitude exceeds the cap.

    Applied to the result of every exact (rational-preserving) operation so a
    value can never grow past the cap without being caught, and so no two
    capped operands can multiply into an uncheckable giant unnoticed."""
    if isinstance(fr, Fraction) and _bits(fr) > MAX_VALUE_BITS:
        raise EvalError("exact value too large to check (> %d bits)" % MAX_VALUE_BITS)
    return fr


def _log2_factorial(n):
    """log2(n!) via lgamma; safe (and fast) for astronomically large n.

    `n` may itself be an over-range Python int (e.g. factorial(power(10, 400))),
    in which case float(n+1) overflows inside lgamma -- caught and reported as
    `inf` (definitely over any cap) rather than crashing."""
    if n <= 1:
        return 0.0
    try:
        return math.lgamma(n + 1) / _LN2
    except OverflowError:
        return math.inf


def _to_float_safe(x):
    """float(x), but map an out-of-range value to +/-inf instead of raising.

    An exact `Fraction` from `power()` with a large integer exponent can be far
    too large to convert to float (its numerator/denominator overflow the
    IEEE-754 range). Both the irrational-op fallbacks (sqrt, fractional power)
    and the relative-tolerance comparison need a value that cannot be exact, so
    mapping an over-range operand to +/-inf is safe: it reads as "no match"
    against any normal-sized number (v2 crashed on exactly this with
    OverflowError)."""
    try:
        return float(x)
    except OverflowError:
        if x > 0:
            return math.inf
        if x < 0:
            return -math.inf
        return 0.0


# --- tokenizer / parser -----------------------------------------------------

_TOKEN_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*|-?\d+\.?\d*|[(),]")


def tokenize(s):
    return _TOKEN_RE.findall(s.strip())


def parse(s):
    """Parse an annotated_formula string into a nested node tree.

    Nodes: ('num', Fraction) | ('const', name) | ('op', name, [args]).
    Raises EvalError on any syntax we do not accept.
    """
    toks = tokenize(s)
    if not toks:
        raise EvalError("empty formula")
    pos = 0

    def peek():
        return toks[pos] if pos < len(toks) else None

    def nxt():
        nonlocal pos
        t = toks[pos]
        pos += 1
        return t

    def expect(t):
        if peek() != t:
            raise EvalError("expected %r, got %r" % (t, peek()))
        nxt()

    def is_number(t):
        return bool(re.fullmatch(r"-?\d+\.?\d*", t or ""))

    def parse_expr():
        t = peek()
        if t is None:
            raise EvalError("unexpected end")
        if is_number(t):
            nxt()
            return ("num", Fraction(t))
        if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", t):
            name = nxt()
            if peek() == "(":
                nxt()  # consume '('
                args = []
                if peek() != ")":
                    args.append(parse_expr())
                    while peek() == ",":
                        nxt()
                        args.append(parse_expr())
                expect(")")
                return ("op", name, args)
            return ("const", name)
        raise EvalError("unexpected token %r" % t)

    node = parse_expr()
    if peek() is not None:
        raise EvalError("trailing tokens: %r" % toks[pos:])
    return node


# --- constants --------------------------------------------------------------

_CONST_NUM_RE = re.compile(r"const_(\d+)(?:_(\d+))?$")


def eval_const(name):
    """Return (value, exact) for a MathQA const_ token.

    Numeric tokens encode their own decimal value: const_100 -> 100 (exact),
    const_3_6 -> 3.6 (exact), const_0_2778 -> 0.2778 (exact). Irrational ones
    fall back to float and are flagged inexact.
    """
    if name == "const_pi":
        return (math.pi, False)
    if name == "const_deg_to_rad":
        return (math.pi / 180.0, False)
    m = _CONST_NUM_RE.match(name)
    if m:
        whole, frac = m.group(1), m.group(2)
        if frac is not None:
            return (Fraction(whole + "." + frac), True)
        return (Fraction(int(whole)), True)
    raise EvalError("unsupported const %r" % name)


# --- operations -------------------------------------------------------------
# Only operations with a single, universally-agreed semantics are implemented.
# Geometry/trig/log operations are deliberately left unsupported (their argument
# conventions are ambiguous), so problems using them are reported as
# "unevaluable (unsupported op)" rather than silently mis-evaluated.

_INT_ONLY = {"gcd", "lcm", "factorial", "choose", "permutation"}


def _as_int(x):
    f = Fraction(x)
    if f.denominator != 1:
        raise EvalError("expected integer, got %s" % f)
    return int(f)


def eval_op(name, args):
    """Return (value, exact). `args` is a list of (value, exact) pairs."""
    vals = [a[0] for a in args]
    ex = all(a[1] for a in args)

    def need(n):
        if len(vals) != n:
            raise EvalError("%s expects %d args, got %d" % (name, n, len(vals)))

    if name == "add":
        need(2); return (_guard(vals[0] + vals[1]), ex)
    if name == "subtract":
        need(2); return (_guard(vals[0] - vals[1]), ex)
    if name == "multiply":
        need(2); return (_guard(vals[0] * vals[1]), ex)
    if name == "divide":
        need(2)
        if vals[1] == 0:
            raise EvalError("divide by zero")
        return (_guard(vals[0] / vals[1]), ex)
    if name == "negate":
        need(1); return (-vals[0], ex)
    if name == "inverse":
        need(1)
        if vals[0] == 0:
            raise EvalError("inverse of zero")
        return (_guard(1 / vals[0] if not ex else Fraction(1, 1) / Fraction(vals[0])), ex)
    if name == "power":
        need(2)
        base, expo = vals[0], vals[1]
        if ex and Fraction(expo).denominator == 1:
            e = int(Fraction(expo))
            if e < 0 and base == 0:
                raise EvalError("0 to negative power")
            bf = Fraction(base)
            # Pre-estimate the result size BEFORE computing it, so a giant
            # integer is never constructed (that is what hung v3). For base not
            # in {0, 1, -1}, base**e has at LEAST (max(nb,db) - 1) * |e| bits,
            # where nb/db are the bit-lengths of |numerator|/|denominator|. That
            # is a true lower bound, so rejecting on it never builds a giant;
            # using the lower (not upper) bound means a legitimately in-cap value
            # like power(2, 60000) is still computed, and the final _guard
            # enforces the exact cap. The compute window (lower<=cap<actual) is
            # at most ~2x cap bits, which is instant to build.
            if bf not in (0, 1, -1):
                lo_bits = (max(bf.numerator.bit_length(),
                               bf.denominator.bit_length()) - 1) * abs(e)
                if lo_bits > MAX_VALUE_BITS:
                    raise EvalError(
                        "power result too large to check (>= %d bits)" % lo_bits)
            return (_guard(bf ** e), True)
        # Inexact (fractional-exponent) power: convert through a safe cast so an
        # over-range exact Fraction operand (e.g. power(power(10, 400), 0.5))
        # cannot raise OverflowError; an out-of-range result reads as inf. A
        # negative base with a fractional exponent yields a complex in Python
        # (e.g. power(negate(2), 0.5)) -- coerce that, and any domain error, to
        # nan so it reads as "no match" rather than crashing float() downstream.
        try:
            r = _to_float_safe(base) ** _to_float_safe(expo)
        except (OverflowError, ValueError, ZeroDivisionError):
            return (math.nan, False)
        if isinstance(r, complex):
            return (math.nan, False)
        return (r, False)
    if name == "min":
        need(2); return (min(vals[0], vals[1]), ex)
    if name == "max":
        need(2); return (max(vals[0], vals[1]), ex)
    if name == "floor":
        need(1); return (Fraction(math.floor(vals[0])), ex)
    if name == "reminder":
        need(2)
        if vals[1] == 0:
            raise EvalError("reminder by zero")
        if ex:
            return (_guard(Fraction(vals[0]) % Fraction(vals[1])), True)
        # Inexact operands may include an over-range exact Fraction; cast safely
        # and tolerate fmod's domain error on a non-finite operand.
        try:
            return (math.fmod(_to_float_safe(vals[0]), _to_float_safe(vals[1])), False)
        except ValueError:
            return (math.nan, False)
    if name == "sqrt":
        need(1)
        # Safe cast: the operand may be an over-range exact Fraction (e.g.
        # sqrt(power(10, 400))) that float() cannot represent.
        fv = _to_float_safe(vals[0])
        if fv < 0:
            raise EvalError("sqrt of negative")
        return (math.sqrt(fv), False)
    if name in _INT_ONLY:
        if name == "factorial":
            need(1); n = _as_int(vals[0])
            if n < 0:
                raise EvalError("factorial of negative")
            # Estimate log2(n!) before computing: factorial(large n) is both
            # astronomically large AND slow to compute, so cap it here. The
            # `n > MAX_VALUE_BITS` short-circuit rejects a huge int operand
            # (e.g. factorial(power(10,400))) with a pure-int comparison, before
            # lgamma would be handed an over-range float.
            if n > MAX_VALUE_BITS or _log2_factorial(n) > MAX_VALUE_BITS:
                raise EvalError("factorial too large to check (n=%d)" % n)
            return (_guard(Fraction(math.factorial(n))), True)
        need(2); a, b = _as_int(vals[0]), _as_int(vals[1])
        if name == "gcd":
            return (Fraction(math.gcd(a, b)), True)
        if name == "lcm":
            if a == 0 or b == 0:
                return (Fraction(0), True)
            return (_guard(Fraction(abs(a * b) // math.gcd(a, b))), True)
        if name == "choose":
            if b < 0 or a < 0 or b > a:
                raise EvalError("choose out of range")
            # log2(C(a,b)) = log2(a!) - log2(b!) - log2((a-b)!); cap before comb.
            # If log2(a!) is inf (a beyond float range) the subtraction would be
            # inf-inf = nan and slip through, so reject outright: math.comb would
            # then run O(min(b,a-b)) big-int multiplies and could hang.
            la = _log2_factorial(a)
            if la == math.inf or la - _log2_factorial(b) - _log2_factorial(a - b) > MAX_VALUE_BITS:
                raise EvalError("choose too large to check (a=%d,b=%d)" % (a, b))
            return (_guard(Fraction(math.comb(a, b))), True)
        if name == "permutation":
            if b < 0 or a < 0 or b > a:
                raise EvalError("permutation out of range")
            # log2(P(a,b)) = log2(a!) - log2((a-b)!); cap before perm (same
            # inf-inf guard as choose).
            la = _log2_factorial(a)
            if la == math.inf or la - _log2_factorial(a - b) > MAX_VALUE_BITS:
                raise EvalError("permutation too large to check (a=%d,b=%d)" % (a, b))
            return (_guard(Fraction(math.perm(a, b))), True)
    raise EvalError("unsupported op %r" % name)


SUPPORTED_OPS = {
    "add", "subtract", "multiply", "divide", "negate", "inverse", "power",
    "min", "max", "floor", "reminder", "sqrt",
    "gcd", "lcm", "factorial", "choose", "permutation",
}

# Operations that keep results exact (rational) when their inputs are exact.
# `power` is exact only with an integer exponent; handled in eval_op.
EXACT_ARITHMETIC_OPS = {"add", "subtract", "multiply", "divide", "negate", "inverse", "power"}


def evaluate(node):
    """Evaluate a parsed node, returning (value, exact). Raises EvalError."""
    kind = node[0]
    if kind == "num":
        return (node[1], True)
    if kind == "const":
        return eval_const(node[1])
    if kind == "op":
        _, name, arg_nodes = node
        args = [evaluate(a) for a in arg_nodes]
        return eval_op(name, args)
    raise EvalError("bad node %r" % (node,))


def collect_names(node, ops, consts):
    """Walk a node tree, accumulating operation and const token names."""
    kind = node[0]
    if kind == "const":
        consts[node[1]] = consts.get(node[1], 0) + 1
    elif kind == "op":
        ops[node[1]] = ops.get(node[1], 0) + 1
        for a in node[2]:
            collect_names(a, ops, consts)


def is_pure_exact_arithmetic(node):
    """True iff the tree uses only literal numbers and EXACT_ARITHMETIC_OPS
    (no const tokens, no sqrt/combinatorics/geometry). Used for the headline
    subset where evaluation is guaranteed exact-rational."""
    kind = node[0]
    if kind == "num":
        return True
    if kind == "const":
        return False
    if kind == "op":
        if node[1] not in EXACT_ARITHMETIC_OPS:
            return False
        return all(is_pure_exact_arithmetic(a) for a in node[2])
    return False


# --- option parsing ---------------------------------------------------------

_OPTION_RE = re.compile(r"([a-e])\s*\)\s*(.*?)(?=(?:,\s*[a-e]\s*\))|$)", re.IGNORECASE | re.DOTALL)
_FRACTION_RE = re.compile(r"^-?\d+\s*/\s*\d+$")
_NUMBER_RE = re.compile(r"-?\d[\d,]*\.?\d*")


def parse_options(options_str):
    """Return {letter: raw_text} parsed from a MathQA options string like
    'a ) 24 , b ) 120 , c ) 625 , d ) 720 , e ) 1024'."""
    out = {}
    for m in _OPTION_RE.finditer(options_str):
        out[m.group(1).lower()] = m.group(2).strip()
    return out


def parse_option_value(text):
    """Parse a single option's numeric value.

    Returns (Fraction, exact=True) or raises EvalError when the option is not a
    clean single number. Handles 'a / b' fractions, thousands commas, a leading
    sign, and trailing units/currency words ('500 kmph', 'Rs. 200', '20 %').
    """
    t = text.strip()
    # Treat as a fraction only when, after dropping non-numeric glyphs, the whole
    # token is essentially 'a / b'. Parse directly from the stripped form: the
    # original text may put a letter/unit between a digit and the slash (e.g.
    # '2nd/3'), in which case a slash-search on the raw text finds nothing even
    # though the value is a clean fraction (this NoneType crash hit v1).
    stripped = re.sub(r"[^\d/\.\-\s]", "", t).strip()
    if _FRACTION_RE.match(stripped):
        num_s, den_s = stripped.split("/")
        den = int(den_s.strip())
        if den == 0:
            raise EvalError("option fraction with zero denominator")
        return (Fraction(int(num_s.strip()), den), True)
    nums = _NUMBER_RE.findall(t)
    cleaned = [n.replace(",", "") for n in nums if n.replace(",", "") not in ("", "-", ".")]
    cleaned = [c for c in cleaned if re.search(r"\d", c)]
    if len(cleaned) != 1:
        raise EvalError("option has %d numbers: %r" % (len(cleaned), text))
    return (Fraction(cleaned[0]), True)


# --- matching ---------------------------------------------------------------

def rel_match(a, b, tol):
    """Relative-tolerance match. tol=0 means exact equality.

    Values may be exact `fractions.Fraction` (possibly astronomically large --
    e.g. power() with a big integer exponent, which overflows float) or float
    (irrational results). When both are rational the comparison is done entirely
    in exact rational arithmetic, so an over-range Fraction never crashes it;
    otherwise it falls back to float with out-of-range values mapped to +/-inf.
    """
    if isinstance(a, Fraction) and isinstance(b, Fraction):
        if tol == 0:
            return a == b
        denom = abs(b) if b != 0 else Fraction(1)
        return abs(a - b) <= Fraction(str(tol)) * denom
    fa, fb = _to_float_safe(a), _to_float_safe(b)
    if tol == 0:
        return fa == fb
    denom = abs(fb) if fb != 0 else 1.0
    return abs(fa - fb) <= tol * denom
