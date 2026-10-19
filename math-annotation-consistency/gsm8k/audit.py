#!/usr/bin/env python3
"""GSM8K calculator-annotation self-consistency audit.

By AI agents working in MV2's name, Munim, Inc. Apache-2.0.

Reads train.jsonl + test.jsonl from openai/grade-school-math and checks two
mechanical, label-free integrity properties of the RELEASED solutions:

  1. Internal arithmetic -- for each inline ``<<expr=result>>`` calculator
     annotation, does ``expr`` evaluate to ``result`` (exactly, or as a
     rounding of ``expr`` to the number of decimals shown)?
  2. Final-answer chain -- does the last annotation's result equal the stated
     ``#### N``, and does ``N`` appear as *some* annotation result?

Expressions are evaluated with a RESTRICTED AST evaluator over exact
``Fraction`` arithmetic -- never ``eval``. Nothing here re-solves a problem or
judges gold-answer correctness; it measures the dataset's OWN self-consistency.

Usage:
    python audit.py --data-dir /data --out-dir /out
"""
import argparse
import ast
import hashlib
import json
import os
import re
import sys
import urllib.request
from decimal import Decimal
from fractions import Fraction

RAW = "https://raw.githubusercontent.com/openai/grade-school-math/master/grade_school_math/data"
SPLITS = {
    "train": RAW + "/train.jsonl",
    "test": RAW + "/test.jsonl",
}

ANNOT_RE = re.compile(r"<<(.*?)>>", re.DOTALL)
HASH_RE = re.compile(r"####\s*(.+?)\s*$", re.DOTALL)
NUM_RE = re.compile(r"[+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?")

MAX_POW = 12  # reject huge powers so a stray exponent cannot blow up memory


class ExprError(Exception):
    pass


# ---------------------------------------------------------------------------
# restricted arithmetic evaluator (exact Fraction; never eval)
# ---------------------------------------------------------------------------
def _normalize_expr(text):
    s = text.strip()
    s = s.replace(",", "")            # thousands separators
    s = s.replace("$", "")
    s = s.replace("×", "*")      # multiplication sign
    s = s.replace("÷", "/")      # division sign
    s = s.replace("−", "-")      # unicode minus
    s = s.replace("^", "**")          # caret power
    s = "".join(s.split())            # drop all internal whitespace
    return s


def _eval_node(node, src):
    if isinstance(node, ast.Expression):
        return _eval_node(node.body, src)
    if isinstance(node, ast.BinOp):
        op = type(node.op)
        left = _eval_node(node.left, src)
        right = _eval_node(node.right, src)
        if op is ast.Add:
            return left + right
        if op is ast.Sub:
            return left - right
        if op is ast.Mult:
            return left * right
        if op is ast.Div:
            if right == 0:
                raise ExprError("division by zero")
            return left / right
        if op is ast.Mod:
            if right == 0:
                raise ExprError("mod by zero")
            return left % right
        if op is ast.Pow:
            if right.denominator != 1:
                raise ExprError("non-integer exponent")
            e = int(right)
            if abs(e) > MAX_POW:
                raise ExprError("exponent too large")
            if left == 0 and e < 0:
                raise ExprError("0 ** negative")
            return Fraction(left) ** e
        raise ExprError("op %s" % op.__name__)
    if isinstance(node, ast.UnaryOp):
        if isinstance(node.op, ast.UAdd):
            return _eval_node(node.operand, src)
        if isinstance(node.op, ast.USub):
            return -_eval_node(node.operand, src)
        raise ExprError("unary %s" % type(node.op).__name__)
    if isinstance(node, ast.Constant):
        if isinstance(node.value, bool) or not isinstance(node.value, (int, float)):
            raise ExprError("const %r" % (node.value,))
        seg = ast.get_source_segment(src, node)
        if seg is None:
            seg = repr(node.value)
        return Fraction(Decimal(seg.strip()))
    raise ExprError("node %s" % type(node).__name__)


def eval_expr(text):
    """Return exact Fraction value of an arithmetic expression, or raise ExprError."""
    s = _normalize_expr(text)
    if not s:
        raise ExprError("empty")
    try:
        tree = ast.parse(s, mode="eval")
    except (SyntaxError, ValueError):
        raise ExprError("syntax")
    try:
        return _eval_node(tree, s)
    except ExprError:
        raise
    except (ZeroDivisionError, OverflowError, ValueError, RecursionError,
            ArithmeticError) as e:
        raise ExprError(str(e))


# ---------------------------------------------------------------------------
# number parsing + exact rounding
# ---------------------------------------------------------------------------
def parse_number(text):
    """Parse a plain decimal result to (Fraction value, n_decimals shown)."""
    t = text.strip().replace(",", "").replace("$", "").replace("%", "")
    t = t.replace("−", "-")
    t = "".join(t.split())
    if not t or not re.fullmatch(r"[+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?", t):
        raise ExprError("non-numeric result")
    dec = Decimal(t)
    exp = dec.as_tuple().exponent
    ndec = -exp if isinstance(exp, int) and exp < 0 else 0
    return Fraction(dec), ndec


def _roundings(y):
    """Return nearest-int roundings of Fraction y under three common modes."""
    n, d = y.numerator, y.denominator
    floor_q = n // d                 # toward -inf
    rem2 = 2 * (n - floor_q * d)     # in [0, 2d)
    if rem2 < d:
        half_up = half_even = floor_q
    elif rem2 > d:
        half_up = half_even = floor_q + 1
    else:  # exactly halfway
        half_up = floor_q + 1 if y > 0 else floor_q      # away from zero
        half_even = floor_q if (floor_q % 2 == 0) else floor_q + 1
    trunc = int(y)                   # toward zero
    return {"half_up": half_up, "half_even": half_even, "trunc": trunc}


def rounds_to(val, res, ndec):
    """True if res equals val rounded to ndec decimals under any common mode."""
    scale = 10 ** ndec
    target = res * scale
    if target.denominator != 1:
        return False
    tgt = target.numerator
    cands = _roundings(val * scale)
    return any(c == tgt for c in cands.values())


def classify(expr_text, result_text):
    try:
        val = eval_expr(expr_text)
    except ExprError:
        return "unparseable_expr", None, None
    try:
        res, ndec = parse_number(result_text)
    except ExprError:
        return "unparseable_result", val, None
    if val == res:
        return "exact", val, res
    if rounds_to(val, res, ndec):
        return "rounding", val, res
    return "mismatch", val, res


# ---------------------------------------------------------------------------
# annotation + chain extraction
# ---------------------------------------------------------------------------
def split_annotation(content):
    """Split <<...>> content into (expr, result) on the LAST '='. None if no '='."""
    if "=" not in content:
        return None
    i = content.rfind("=")
    return content[:i], content[i + 1:]


def final_answer(answer):
    m = HASH_RE.search(answer)
    if not m:
        return None
    try:
        res, _ = parse_number(m.group(1))
        return res
    except ExprError:
        return None


# ---------------------------------------------------------------------------
# main audit
# ---------------------------------------------------------------------------
def fetch_split(name, data_dir):
    path = os.path.join(data_dir, name + ".jsonl")
    if not os.path.exists(path):
        os.makedirs(data_dir, exist_ok=True)
        urllib.request.urlretrieve(SPLITS[name], path)
    with open(path, "rb") as f:
        raw = f.read()
    sha = hashlib.sha256(raw).hexdigest()
    rows = [json.loads(line) for line in raw.decode("utf-8").splitlines() if line.strip()]
    return rows, sha, len(raw)


def audit_split(name, rows):
    classes = {"exact": 0, "rounding": 0, "mismatch": 0, "no_equals": 0,
               "unparseable_expr": 0, "unparseable_result": 0}
    n_ann = 0
    n_with_ann = 0
    last_matches = 0
    appears = 0
    final_unparseable = 0
    bad_annotations = []   # mismatch / unparseable
    chain_breaks = []      # last != final, or final missing from results

    for idx, row in enumerate(rows):
        ans = row.get("answer", "")
        ann_texts = ANNOT_RE.findall(ans)
        results = []  # Fraction results in order (None where unknown)
        for a in ann_texts:
            n_ann += 1
            parts = split_annotation(a)
            if parts is None:
                classes["no_equals"] += 1
                results.append(None)
                continue
            expr_text, result_text = parts
            cls, val, res = classify(expr_text, result_text)
            classes[cls] += 1
            results.append(res)
            if cls in ("mismatch", "unparseable_expr", "unparseable_result"):
                if len(bad_annotations) < 5000:
                    bad_annotations.append({
                        "split": name, "index": idx, "annotation": a,
                        "expr": expr_text, "result": result_text, "class": cls,
                        "expr_value": (str(val) if val is not None else None),
                    })

        fin = final_answer(ans)
        if not ann_texts:
            # problems with no annotations still have a #### ; count chain only
            # where there is at least one annotation
            if fin is None:
                final_unparseable += 1
            continue
        n_with_ann += 1
        if fin is None:
            final_unparseable += 1
            continue
        last_res = next((r for r in reversed(results) if r is not None), None)
        matched = (last_res is not None and last_res == fin)
        in_results = any(r is not None and r == fin for r in results)
        if matched:
            last_matches += 1
        if in_results:
            appears += 1
        if not matched or not in_results:
            if len(chain_breaks) < 5000:
                chain_breaks.append({
                    "split": name, "index": idx,
                    "last_result": (str(last_res) if last_res is not None else None),
                    "final": str(fin),
                    "last_matches": matched,
                    "final_in_results": in_results,
                })

    n = len(rows)
    exact = classes["exact"]
    rounding = classes["rounding"]
    good = exact + rounding
    summary = {
        "split": name,
        "n_problems": n,
        "n_problems_with_annotations": n_with_ann,
        "n_annotations": n_ann,
        "classes": classes,
        "exact_rate": (exact / n_ann if n_ann else None),
        "exact_or_rounding_rate": (good / n_ann if n_ann else None),
        "mismatch_rate": (classes["mismatch"] / n_ann if n_ann else None),
        "last_matches_count": last_matches,
        "last_matches_rate": (last_matches / n_with_ann if n_with_ann else None),
        "final_appears_count": appears,
        "final_appears_rate": (appears / n_with_ann if n_with_ann else None),
        "final_unparseable_count": final_unparseable,
    }
    return summary, bad_annotations, chain_breaks


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default="/data")
    ap.add_argument("--out-dir", default="/out")
    args = ap.parse_args()
    os.makedirs(args.out_dir, exist_ok=True)

    per_split = []
    catalog = {"bad_annotations": [], "chain_breaks": []}
    sources = {}
    for name in ("train", "test"):
        rows, sha, nbytes = fetch_split(name, args.data_dir)
        sources[name] = {"url": SPLITS[name], "sha256": sha, "n_bytes": nbytes,
                         "n_rows": len(rows)}
        s, bad, breaks = audit_split(name, rows)
        per_split.append(s)
        catalog["bad_annotations"].extend(bad)
        catalog["chain_breaks"].extend(breaks)
        print("[%s] problems=%d annotations=%d exact=%d rounding=%d mismatch=%d "
              "no_eq=%d unparse_expr=%d unparse_res=%d | last_matches=%d/%d appears=%d/%d"
              % (name, s["n_problems"], s["n_annotations"], s["classes"]["exact"],
                 s["classes"]["rounding"], s["classes"]["mismatch"],
                 s["classes"]["no_equals"], s["classes"]["unparseable_expr"],
                 s["classes"]["unparseable_result"], s["last_matches_count"],
                 s["n_problems_with_annotations"], s["final_appears_count"],
                 s["n_problems_with_annotations"]))

    # combined totals
    tot_classes = {k: sum(s["classes"][k] for s in per_split) for k in per_split[0]["classes"]}
    tot_ann = sum(s["n_annotations"] for s in per_split)
    tot_prob = sum(s["n_problems"] for s in per_split)
    tot_with = sum(s["n_problems_with_annotations"] for s in per_split)
    tot_lastm = sum(s["last_matches_count"] for s in per_split)
    tot_app = sum(s["final_appears_count"] for s in per_split)
    good = tot_classes["exact"] + tot_classes["rounding"]
    total = {
        "n_problems": tot_prob,
        "n_problems_with_annotations": tot_with,
        "n_annotations": tot_ann,
        "classes": tot_classes,
        "exact_rate": (tot_classes["exact"] / tot_ann if tot_ann else None),
        "exact_or_rounding_rate": (good / tot_ann if tot_ann else None),
        "mismatch_rate": (tot_classes["mismatch"] / tot_ann if tot_ann else None),
        "last_matches_count": tot_lastm,
        "last_matches_rate": (tot_lastm / tot_with if tot_with else None),
        "final_appears_count": tot_app,
        "final_appears_rate": (tot_app / tot_with if tot_with else None),
    }

    summary = {
        "artifact": "gsm8k-annotation-audit",
        "by": "AI agents working in MV2's name, Munim, Inc.",
        "method": "restricted-AST exact-Fraction evaluation of each <<expr=result>> "
                  "annotation; last-annotation-to-#### chain check. No re-solving.",
        "sources": sources,
        "per_split": per_split,
        "total": total,
        "catalog_counts": {
            "bad_annotations": len(catalog["bad_annotations"]),
            "chain_breaks": len(catalog["chain_breaks"]),
        },
    }
    with open(os.path.join(args.out_dir, "summary.json"), "w") as f:
        json.dump(summary, f, indent=1)
    with open(os.path.join(args.out_dir, "catalog.json"), "w") as f:
        json.dump(catalog, f, indent=1)
    print("TOTAL exact_or_rounding_rate=%s mismatch=%d last_matches_rate=%s" % (
        total["exact_or_rounding_rate"], tot_classes["mismatch"],
        total["last_matches_rate"]))
    print("wrote summary.json + catalog.json to", args.out_dir)


if __name__ == "__main__":
    sys.exit(main())
