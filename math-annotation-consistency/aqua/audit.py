"""AQuA-RAT rationale inline-arithmetic self-consistency audit (core logic).

AQuA-RAT (Ling et al., 2017; google-deepmind/AQuA) is a ~100k algebraic
word-problem dataset. Each record has a free-text `rationale` that writes its
arithmetic inline as prose equations, e.g. "43/2.15 = 20", "36 * 5/18 = 10 m/s".
This module asks the SAME self-consistency question MV2 asked of GSM8K's
`<<expr=result>>` tags, but of AQuA's free-text annotation style: inside a single
written equation `LHS = RHS`, does the exact arithmetic of a compound left side
actually equal the plain number written on the right?

It does NOT check whether the rationale reaches the correct option (Calc-X,
Kadlcik et al. EMNLP 2023 arXiv:2305.15017, already covers option-consistency).
What is unpublished is the INTERNAL inline-equation error rate, with a labelled
catalogue separating genuine arithmetic slips from ordinary rounding.

v4 — false-positive hardening (motivated by a hand spot-check of v3's catalogue,
documented in aqua-v3-grading.md). v3 aimed at zero false positives but its
catalogue still contained four classes of extraction artifact, because a numeric
"run" cut out of surrounding prose can look like a wrong equation when it is not.
v4 removes those classes by checking each run's immediate neighbouring characters
in the normalized text and by setting aside precedence-ambiguous linearizations:

  1. RATIO fragments. "1/7:1/7:1/14 = 2:2:1" — the colon ends a run, leaving the
     fragment "1/14 = 2". A step whose left operand abuts a ':' (or whose right
     operand abuts a ':') is part of a ratio/proportion, not an equation -> skip.
  2. STRIPPED RADICALS. "sqrt(3)/4 * 16 * 16 = 64*sqrt(3)" with a Unicode radical
     glyph: the glyph ends the run, leaving "3/4*16*16 = 64". An operand abutting
     a radical glyph has lost part of its value -> skip.
  3. 'x'-AS-TIMES SPLITS. "5358 x 51 = 5358 x (50+1)" uses the letter 'x' for
     multiplication; the letter ends the run, leaving "(50+1) = 5358" (where 5358
     is really "5358 x ..."). A right operand immediately followed by a lone 'x'
     that continues into more math -> the value is truncated -> skip.
  4. PRECEDENCE-AMBIGUOUS LINEARIZATIONS. "7*6*5 / 3*2 = 35" means (7*6*5)/(3*2);
     read strictly left-to-right it is 140. When a top-level '/' is followed by a
     top-level '*' (no parentheses to disambiguate), the written order does not
     fix the grouping -> set aside as `ambiguous`, never flagged as an error.

Everything else is unchanged from v3, including the magnitude guards that stop a
free-text power tower from timing the job out. Exact values are carried as
`fractions.Fraction`; a step is `exact` iff LHS and RHS are rational-equal.
Standard library only. Import-only; `job.py` drives it.
"""

from __future__ import annotations

import re
from fractions import Fraction


class EvalError(Exception):
    """Raised when an expression cannot be evaluated by the exact grammar."""


# Magnitude guards (from v3): a free-text run can encode a power tower whose value
# or exponent is astronomically large; computing it times the job out and overflows
# float. An exponent cap and a result-size cap keep every audited value comparable
# via float. The bounds are far above any genuine inline arithmetic step.
_MAX_POWER_EXPONENT = 512
_MAX_VALUE_BITS = 900  # 2^900 ~= 10^271 < float max; float() stays safe


def _too_big(fr):
    try:
        return (fr.numerator.bit_length() > _MAX_VALUE_BITS
                or fr.denominator.bit_length() > _MAX_VALUE_BITS)
    except AttributeError:
        return False


# --- cleaning ---------------------------------------------------------------

# Unicode radical glyphs. These are normalized to a sentinel 'R' so that (a) the
# run regex (which has no 'R') still breaks on them exactly where v3 broke, and
# (b) a step touching one can be recognised as "radical was here" and skipped.
_RADICALS = "√∛∜"  # sqrt, cube root, fourth root
_RADICAL_SENTINEL = "R"


def normalize_text(s):
    """Normalise unicode math glyphs to ASCII operators and flatten newlines.

    Radical glyphs become the sentinel 'R' (a letter, so it ends a run exactly as
    the raw glyph did) to mark radical-adjacent operands for skipping."""
    if not s:
        return ""
    s = s.replace("×", "*").replace("·", "*").replace("∗", "*")
    s = s.replace("÷", "/").replace("∕", "/")
    s = s.replace("−", "-").replace("–", "-").replace("—", "-")
    for r in _RADICALS:
        s = s.replace(r, _RADICAL_SENTINEL)
    s = s.replace("\r", " ").replace("\n", " ").replace("\t", " ")
    return s


def clean_side(s):
    """Value-preserving cleanup of one side: drop '$' and thousands commas,
    collapse spaces. Does NOT touch '%'."""
    s = s.replace("$", "")
    s = re.sub(r"(?<=\d),(?=\d)", "", s)   # thousands commas only
    s = s.replace(",", " ")                # any other comma -> separator
    return s.strip()


# --- exact infix evaluator --------------------------------------------------
# Recursive-descent over + - * / ^ ( ) with unary minus. Values are Fractions.
# Returns (value, nops) where nops counts applied binary ops / powers.

_NUM_RE = re.compile(r"\d+\.?\d*|\.\d+")


def _tokenize(s):
    toks = []
    i, n = 0, len(s)
    while i < n:
        c = s[i]
        if c.isspace():
            i += 1
            continue
        if c in "+-*/^()":
            toks.append(c)
            i += 1
            continue
        m = _NUM_RE.match(s, i)
        if m:
            toks.append(m.group(0))
            i = m.end()
            continue
        raise EvalError("bad char %r in %r" % (c, s))
    return toks


def eval_expr(s):
    """Evaluate an arithmetic string exactly. Returns (Fraction, nops)."""
    toks = _tokenize(s)
    if not toks:
        raise EvalError("empty expression")
    pos = 0
    nops = 0

    def peek():
        return toks[pos] if pos < len(toks) else None

    def nxt():
        nonlocal pos
        t = toks[pos]
        pos += 1
        return t

    def parse_expr():
        nonlocal nops
        v = parse_term()
        while peek() in ("+", "-"):
            op = nxt()
            rhs = parse_term()
            v = v + rhs if op == "+" else v - rhs
            nops += 1
        return v

    def parse_term():
        nonlocal nops
        v = parse_factor()
        while peek() in ("*", "/"):
            op = nxt()
            rhs = parse_factor()
            if op == "*":
                v = v * rhs
            else:
                if rhs == 0:
                    raise EvalError("divide by zero")
                v = v / rhs
            nops += 1
        return v

    def parse_factor():
        nonlocal nops
        base = parse_base()
        if peek() == "^":
            nxt()
            expo = parse_factor()  # right-assoc
            if expo.denominator != 1:
                raise EvalError("non-integer exponent")
            e = int(expo)
            if e < 0 and base == 0:
                raise EvalError("0 to negative power")
            if abs(e) > _MAX_POWER_EXPONENT:
                raise EvalError("exponent too large to verify: %d" % e)
            nops += 1
            result = base ** e
            if _too_big(result):
                raise EvalError("power result too large to verify")
            return result
        return base

    def parse_base():
        t = peek()
        if t is None:
            raise EvalError("unexpected end")
        if t == "-":
            nxt()
            return -parse_base()
        if t == "+":
            nxt()
            return parse_base()
        if t == "(":
            nxt()
            v = parse_expr()
            if peek() != ")":
                raise EvalError("missing )")
            nxt()
            return v
        if _NUM_RE.fullmatch(t):
            nxt()
            return Fraction(t)
        raise EvalError("unexpected token %r" % t)

    value = parse_expr()
    if peek() is not None:
        raise EvalError("trailing tokens %r" % toks[pos:])
    return value, nops


_BARE_NUM_RE = re.compile(r"^[+-]?(?:\d+\.?\d*|\.\d+)$")


def is_bare_number(s):
    return bool(_BARE_NUM_RE.match(s.strip()))


def has_ambiguous_precedence(expr):
    """True if, at parenthesis depth 0, a '/' is followed later by a '*' (or a
    second '/'), so the written order does not determine the grouping. v4 sets
    such linearizations aside rather than flagging them as arithmetic errors."""
    depth = 0
    seen_div = False
    for c in expr:
        if c == "(":
            depth += 1
        elif c == ")":
            depth = max(0, depth - 1)
        elif depth == 0:
            if c == "/":
                if seen_div:
                    return True
                seen_div = True
            elif c == "*" and seen_div:
                return True
    return False


# --- equation extraction ----------------------------------------------------

# A maximal run of chars that can appear in a numeric equation. Any letter (incl.
# the radical sentinel 'R' and an 'x' used as times) ends the run.
_RUN_RE = re.compile(r"[0-9.,%$()+\-*/^=\s]+")


def extract_runs(rationale):
    """Yield (run_text, left_ctx, right_ctx, right_ctx2) for each candidate
    equation run. left_ctx is the char immediately before the run (or ""),
    right_ctx the char immediately after (or ""), right_ctx2 the one after that.
    Because the run is maximal over allowed chars, those context chars are the
    disallowed, non-space characters that bound the run in the source."""
    text = normalize_text(rationale)
    n = len(text)
    for m in _RUN_RE.finditer(text):
        run = m.group(0)
        if "=" not in run:
            continue
        if not re.search(r"\d", run):
            continue
        if not re.search(r"[+\-*/^]", run):
            continue
        s, e = m.start(), m.end()
        lc = text[s - 1] if s > 0 else ""
        rc = text[e] if e < n else ""
        rc2 = text[e + 1] if e + 1 < n else ""
        yield run.strip(), lc, rc, rc2


def rel_diff(a, b):
    """Relative difference |a-b|/|b|. Callers keep a,b within _MAX_VALUE_BITS."""
    fa, fb = float(a), float(b)
    denom = abs(fb) if fb != 0 else (abs(fa) if fa != 0 else 1.0)
    return abs(fa - fb) / denom


def _left_truncated(lc):
    """Left operand abuts a ratio colon, a radical, or a lone 'x'/'X' used as a
    times-operator (so the operand is a middle factor, not a full side). Only
    these high-confidence mechanical cuts are dropped; an equation merely
    following a prose word (lc is some other letter) is kept and audited."""
    return lc == ":" or lc == _RADICAL_SENTINEL or lc in ("x", "X")


def _right_truncated(rc, rc2):
    """Right operand is truncated by the source: a ratio colon, a radical, or a
    lone 'x'/'X' used as a times-operator that continues into more arithmetic.
    A trailing unit word (e.g. '10 m/s', '4.15 hrs') is NOT a truncation."""
    if rc == ":" or rc == _RADICAL_SENTINEL:
        return True
    if rc in ("x", "X"):
        # 'x' as times iff what follows is whitespace / a digit / '(' / nothing,
        # i.e. the expression keeps going. "x" starting a unit word (e.g. none in
        # AQuA) would be followed by another letter and is left alone.
        return rc2 == "" or rc2.isspace() or rc2.isdigit() or rc2 == "("
    return False


def audit_rationale(rationale):
    """Return a list of audited step dicts for one rationale.

    status: 'ok' (audited numeric step), 'percent' / 'ambiguous' / 'unevaluable'
    (set aside), 'skip_boundary' (dropped as an extraction artifact; not counted).
    """
    steps = []
    for run, lc, rc, rc2 in extract_runs(rationale):
        parts = run.split("=")
        npairs = len(parts) - 1
        for i in range(npairs):
            left_raw, right_raw = parts[i], parts[i + 1]
            is_first = (i == 0)
            is_last = (i == npairs - 1)

            # Boundary artifacts: a truncated operand is not a real equation side.
            if is_first and _left_truncated(lc):
                continue
            if is_last and _right_truncated(rc, rc2):
                continue

            # percent changes value -> set aside before cleaning strips nothing
            if "%" in left_raw or "%" in right_raw:
                if re.search(r"[+\-*/^]", left_raw):
                    steps.append({"left": left_raw.strip(),
                                  "right": right_raw.strip(), "status": "percent"})
                continue
            left = clean_side(left_raw)
            right = clean_side(right_raw)
            if not is_bare_number(right):
                continue
            if not re.search(r"[+\-*/^]", left):
                continue  # left not a compound expression -> trivial restatement
            if has_ambiguous_precedence(left):
                steps.append({"left": left, "right": right, "status": "ambiguous"})
                continue
            try:
                lval, nops = eval_expr(left)
            except EvalError:
                steps.append({"left": left, "right": right, "status": "unevaluable"})
                continue
            if nops == 0:
                continue  # no operation actually applied
            try:
                rval = Fraction(right)
            except (ValueError, ZeroDivisionError):
                continue
            if _too_big(lval) or _too_big(rval):
                steps.append({"left": left, "right": right, "status": "unevaluable"})
                continue
            steps.append({
                "left": left, "right": right, "status": "ok",
                "exact": (lval == rval),
                "reldiff": rel_diff(lval, rval),
                "leftval": float(lval), "rightval": float(rval),
            })
    return steps
