# SPDX-License-Identifier: Apache-2.0
# Audit 119 (pre-registered) by MV2 of Munim, Inc. Made with AI agents working in MV2's name.
#
# exact_match is transcribed from HELM's src/helm/benchmark/metrics/evaluate_reference_metrics.py
# (stanford-crfm/helm main, read 2026-11-14), with the max over correct references from
# compute_metrics_helper. HELM is Apache-2.0 (Stanford CRFM). The float/integer normalisation in
# official_float / official_int follows MathVista's evaluation/calculate_score.py
# (lupantech/MathVista, normalize_extracted_answer), which uses str(round(float(x), precision)) and
# str(int(float(x))).
"""VHELM's MathVista free-form runs: what does strict exact match leave uncredited?

HELM's math_vista scenario sends MathVista's bare `question` (not its `query`, which carries the
"Hint:" line naming an integer or a float with one/two decimals, and the unit), asks "Just give the
numerical answer without showing the steps, the unit, or percentage symbol." with max_tokens=20, and
reports exact_match (gold.strip() == pred.strip()). This module classifies every uncredited answer.
"""
import hashlib
import math
import re
from decimal import Decimal, InvalidOperation
from fractions import Fraction

STAT = "exact_match"
GRADES = ("college", "daily_life", "elementary_school", "high_school")
CLASSES = ("exact", "num_equal", "rounds_to_gold", "int_trunc_official", "last_number_equal",
           "wrong_number", "no_number", "other", "empty", "nonnumeric_gold")
LENIENT = ("exact", "num_equal", "rounds_to_gold")
TAGS = ("wrapped", "period", "symbol", "unit", "separator", "number_form")

_NUM = re.compile(r"[-+]?(?:\d+(?:\.\d+)?|\.\d+)")
_SEP = re.compile(r"[-+]?\d{1,3}(?:,\d{3})+(?:\.\d+)?")
_ANYNUM = re.compile(r"-?\d+(?:\.\d+)?")


# ---------------- transcribed from HELM (Apache-2.0) ----------------
def exact_match(gold, pred):
    if not pred:
        return 0
    return 1 if gold.strip() == pred.strip() else 0


def helm_score(golds, pred):
    """max over correct references of exact_match(gold, pred.strip()), as in compute_metrics_helper."""
    p = (pred or "").strip()
    return max(exact_match(g or "", p) for g in golds) if golds else 0


# ---------------- MathVista official normalisation (calculate_score.py) ----------------
def official_float(x, precision):
    try:
        return str(round(float(x), int(precision)))
    except (ValueError, TypeError, OverflowError):
        return None


def official_int(x):
    try:
        return str(int(float(x)))
    except (ValueError, TypeError, OverflowError):
        return None


# ---------------- ours ----------------
def to_decimal(s):
    """Decimal of a plain number string (None unless the whole string is one number)."""
    s = (s or "").strip()
    if not _NUM.fullmatch(s):
        return None
    try:
        return Decimal(s)
    except InvalidOperation:
        return None


def decimals_of(s):
    """Digits after the decimal point in a plain number string (0 for integers)."""
    s = (s or "").strip()
    return len(s.split(".", 1)[1]) if "." in s else 0


def gold_info(golds):
    """(numeric gold string or None, its Decimal, its precision, unit word or None)."""
    num = None
    for g in golds:
        if to_decimal(g) is not None:
            num = g.strip()
            break
    if num is None:
        return None, None, None, None
    unit = None
    for g in golds:
        g = (g or "").strip()
        if g != num and g.startswith(num + " "):
            unit = g[len(num) + 1:].strip() or None
    return num, to_decimal(num), decimals_of(num), unit


def _unwrap(s, tags):
    changed = True
    while changed:
        changed = False
        s = s.strip()
        for a, b in (("\\(", "\\)"), ("\\[", "\\]"), ("$$", "$$"), ("**", "**"), ("$", "$")):
            if len(s) > len(a) + len(b) and s.startswith(a) and s.endswith(b):
                s = s[len(a):len(s) - len(b)]
                tags.add("wrapped")
                changed = True
                break
        m = re.fullmatch(r"\\boxed\{(.*)\}", s)
        if not changed and m:
            s = m.group(1)
            tags.add("wrapped")
            changed = True
    return s.strip()


def parse_answer(pred, unit=None):
    """(Decimal, cleaned string, tags) when the answer is one number after format-only cleaning, else
    (None, None, tags). Cleaning: LaTeX/markdown wrappers, one trailing period, %, degree signs, a leading
    currency $, a unicode minus, the instance's own unit word, and thousands separators."""
    tags = set()
    s = (pred or "").strip()
    if not s:
        return None, None, tags
    s = _unwrap(s, tags)
    if s.endswith(".") and len(s) > 1 and s[-2].isdigit():
        s = s[:-1].rstrip()
        tags.add("period")
    if "\u2212" in s:
        s = s.replace("\u2212", "-")
        tags.add("symbol")
    for suf in ("\\%", "%", "^{\\circ}", "^\\circ", "\u00b0"):
        if s.endswith(suf):
            s = s[: -len(suf)].rstrip()
            tags.add("symbol")
            break
    if s.startswith("$") and not s.endswith("$"):
        s = s[1:].strip()
        tags.add("symbol")
    if unit and s.lower().endswith(" " + unit.lower()):
        s = s[: -len(unit)].rstrip()
        tags.add("unit")
    if _SEP.fullmatch(s):
        s = s.replace(",", "")
        tags.add("separator")
    d = to_decimal(s)
    if d is None:
        return None, None, tags
    return d, s, tags


def last_number(pred):
    """Decimal of the last number in free text (thousands separators between digits removed)."""
    t = re.sub(r"(?<=\d),(?=\d{3}\b)", "", (pred or "").replace("\u2212", "-"))
    found = _ANYNUM.findall(t)
    if not found:
        return None
    try:
        return Decimal(found[-1])
    except InvalidOperation:
        return None


def classify(golds, pred, stored):
    """(class, tags, parsed-number decimals or None). `stored` is the stored exact_match (0/1)."""
    if stored >= 0.5:
        num, _, _, unit = gold_info(golds)
        d, s, _ = parse_answer(pred, unit)
        return "exact", set(), (decimals_of(s) if d is not None else None)
    p = (pred or "").strip()
    if not p:
        return "empty", set(), None
    num, gd, prec, unit = gold_info(golds)
    if num is None:
        return "nonnumeric_gold", set(), None
    d, s, tags = parse_answer(p, unit)
    if d is not None:
        nd = decimals_of(s)
        if d == gd:
            if s != num and not tags:
                tags.add("number_form")
            return "num_equal", tags, nd
        if prec >= 1 and nd > prec and official_float(s, prec) == num:
            return "rounds_to_gold", tags, nd
        if prec == 0 and nd >= 1 and official_int(s) == num:
            return "int_trunc_official", tags, nd
        return "wrong_number", tags, nd
    ln = last_number(p)
    if ln is None:
        return "no_number", set(), None
    if ln == gd:
        return "last_number_equal", set(), None
    return "other", set(), None


def is_number(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool) and not (isinstance(v, float) and math.isnan(v))


def stat_entry(stats, name, split="test"):
    """{count, sum, mean} of the unperturbed stat `name` on `split` in a HELM stats.json list (None when absent)."""
    for s in stats or []:
        if not isinstance(s, dict):
            continue
        nm = s.get("name") or {}
        if (nm.get("name") == name and nm.get("split") == split and nm.get("perturbation") is None
                and nm.get("sub_split") is None):
            return {"count": s.get("count"), "sum": s.get("sum"), "mean": s.get("mean")}
    return None


def question_of(instance):
    inp = (instance or {}).get("input") or {}
    mc = inp.get("multimedia_content") or {}
    for mo in mc.get("media_objects") or []:
        if isinstance(mo, dict) and str(mo.get("content_type", "")).startswith("text") and mo.get("text"):
            return mo["text"]
    return inp.get("text") or ""


def golds_of(instance):
    out = []
    for ref in (instance or {}).get("references") or []:
        if isinstance(ref, dict) and "correct" in (ref.get("tags") or []):
            out.append((ref.get("output") or {}).get("text") or "")
    return out


def gold_kind(golds):
    num, _, prec, _ = gold_info(golds)
    if num is None:
        return "list" if any((g or "").strip().startswith("[") for g in golds) else "other"
    return "float" if prec >= 1 else "integer"


def instance_map(instances):
    """{test id: (gold kind, tuple of golds, has_hint)}; has_hint = the sent question contains 'Hint:'."""
    out = {}
    for i in instances or []:
        if isinstance(i, dict) and i.get("split") == "test":
            golds = tuple(golds_of(i))
            out[i.get("id")] = (gold_kind(golds), golds, "hint:" in question_of(i).lower())
    return out


def run_field(run_name, key):
    i = run_name.find(key + "=")
    return run_name[i + len(key) + 1:].split(",")[0] if i >= 0 else ""


def summarize_run(preds, imap, max_tokens):
    """Census of one run's display_predictions (unperturbed, test ids only, first record per instance)."""
    counts = {"n_records": 0, "perturbed": 0, "not_test": 0, "duplicate": 0, "kept": 0,
              "stored_missing": 0, "mismatch": 0, "credit": 0, "cap": 0}
    classes = {c: 0 for c in CLASSES}
    cap_by_class = {c: 0 for c in CLASSES}
    tags = {t: 0 for t in TAGS}
    by_kind = {k: {"n": 0, "credit": 0, "lenient": 0} for k in ("integer", "float", "list", "other")}
    float_single = {"n": 0, "other_decimals": 0}
    examples = {c: [] for c in ("num_equal", "rounds_to_gold", "last_number_equal", "int_trunc_official")}
    seen = set()
    for r in preds or []:
        if not isinstance(r, dict):
            continue
        counts["n_records"] += 1
        if r.get("perturbation") is not None:
            counts["perturbed"] += 1
            continue
        iid = r.get("instance_id")
        if iid not in imap:
            counts["not_test"] += 1
            continue
        if iid in seen:
            counts["duplicate"] += 1
            continue
        seen.add(iid)
        counts["kept"] += 1
        kind, golds, _ = imap[iid]
        pred = r.get("predicted_text") or ""
        st = r.get("stats") or {}
        ours = helm_score(golds, pred)
        v = st.get(STAT)
        if not is_number(v):
            counts["stored_missing"] += 1
            v = 0
        elif abs(v - ours) > 1e-9:
            counts["mismatch"] += 1
        credit = 1 if v >= 0.5 else 0
        counts["credit"] += credit
        cls, tg, nd = classify(golds, pred, credit)
        classes[cls] += 1
        for t in tg:
            tags[t] += 1
        nout = st.get("num_output_tokens")
        cap = bool(max_tokens) and is_number(nout) and nout >= max_tokens
        if cap:
            counts["cap"] += 1
            cap_by_class[cls] += 1
        b = by_kind[kind]
        b["n"] += 1
        b["credit"] += credit
        b["lenient"] += 1 if cls in LENIENT else 0
        if kind == "float" and nd is not None:
            _, _, prec, _ = gold_info(golds)
            float_single["n"] += 1
            if nd != prec:
                float_single["other_decimals"] += 1
        if cls in examples and len(examples[cls]) < 3:
            examples[cls].append((iid, golds[0] if golds else "", pred[:60]))
    lenient = sum(classes[c] for c in LENIENT)
    return {"counts": counts, "classes": classes, "cap_by_class": cap_by_class, "tags": tags, "by_kind": by_kind,
            "float_single": float_single, "lenient": lenient, "examples": examples}


def ranks_high(values):
    """Higher is better: rank = 1 + the number of entries strictly higher (exact values)."""
    return {k: 1 + sum(1 for w in values.values() if w > v) for k, v in values.items()}


def kendall_tau_b(xs, ys):
    """Kendall's tau-b of two equal-length sequences (None when either is constant or shorter than 2)."""
    n = len(xs)
    c = d = tx = ty = 0
    for i in range(n):
        for j in range(i + 1, n):
            dx = (xs[i] > xs[j]) - (xs[i] < xs[j])
            dy = (ys[i] > ys[j]) - (ys[i] < ys[j])
            if dx == 0:
                tx += 1
            if dy == 0:
                ty += 1
            if dx and dy:
                if dx == dy:
                    c += 1
                else:
                    d += 1
    n0 = n * (n - 1) // 2
    den = (n0 - tx) * (n0 - ty)
    return (c - d) / math.sqrt(den) if den > 0 else None


def stable_hash(text):
    return int(hashlib.sha256(text.encode("utf-8")).hexdigest()[:12], 16)


# ---------------- Verdicts ----------------
def verdicts(s):
    """The eight pre-registered predictions (True = HELD, False = FAILED, None = not gradable)."""
    def ge(a, b):
        return None if a is None else a >= b

    rec = s.get("pooled_records") or 0
    fmt = s.get("pooled_num_equal", 0) + s.get("pooled_rounds_to_gold", 0)
    fs_n, fs_o = s.get("float_single_n") or 0, s.get("float_single_other") or 0
    tau = s.get("tau_b")
    gain = s.get("max_gain")
    return {
        "P1": (s["runs_listed"] == 204 and s["runs_included"] * 100 >= 95 * s["runs_listed"]
               and s.get("models_complete", 0) >= 48),
        "P2": ge(s.get("pooled_num_equal") if rec else None, 50),
        "P3": None if not rec else fmt * 100 <= 3 * rec,
        "P4": ge(s.get("pooled_rounds_to_gold") if rec else None, 20),
        "P5": None if not fs_n else fs_o * 5 >= fs_n,
        "P6": ge(s.get("models_cap2") if rec else None, 10),
        "P7": None if tau is None else tau >= 0.90,
        "P8": None if gain is None else gain >= Fraction(3, 100),
    }


def verdict_word(v):
    return "NOT GRADED" if v is None else ("HELD" if v else "FAILED")
