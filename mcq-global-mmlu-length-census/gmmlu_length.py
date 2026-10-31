"""Global-MMLU LENGTH census (audit 70): culturally sensitive vs agnostic questions, and 42 languages.

Audits 52 and 60 found that MMLU carries a small "pick the longest option" shortcut (0.2805 vs 0.25 chance pooled),
concentrated in a law/clinical/social cluster of subjects. Global-MMLU (Singh et al. 2024, arXiv 2412.03304;
Apache-2.0) translates MMLU's 14,042 test questions into 42 languages and labels 2,850 of them as Culturally
Sensitive (CS) or Culturally Agnostic (CA). Its paper reports no answer-length analysis. This module measures:

- the length floor (tie-aware pick-longest / pick-shortest accuracy vs chance) per CS/CA label and subject category;
- the CS minus CA difference in pick-longest lift, raw and stratified by subject;
- per language, how the floor, the answer keys and the identity of the unique longest option compare with English;
- whether Global-MMLU's English rows are MMLU's test rows (options and key), joined by sample_id.

Lengths are characters after stripping, exactly as in mcq-length-floor 0.1.0. Standard library only. Apache-2.0.
Authored by AI agents working in the name of MV2, Munim, Inc.
"""

import math
from fractions import Fraction

LETTERS = "ABCD"
OPTION_COLS = ("option_a", "option_b", "option_c", "option_d")
LABELS = ("CS", "CA")
UNLABELLED = "unlabelled"


# ----- one question -----

def length(option):
    return len(str(option).strip())


def credits(options, gold):
    """(pick-longest credit, pick-shortest credit), each tie-aware: 1/t when the gold is one of t tied extremes."""
    L = [length(o) for o in options]
    hi, lo = max(L), min(L)
    cl = Fraction(1, L.count(hi)) if L[gold] == hi else Fraction(0)
    cs = Fraction(1, L.count(lo)) if L[gold] == lo else Fraction(0)
    return cl, cs


def unique_longest(options):
    """Index of the unique longest option, or None when the longest length is tied."""
    L = [length(o) for o in options]
    hi = max(L)
    return L.index(hi) if L.count(hi) == 1 else None


def key_index(answer):
    """'A'..'D' (any case, outer spaces ignored) -> 0..3; anything else -> None."""
    s = "" if answer is None else str(answer).strip().upper()
    return LETTERS.index(s) if len(s) == 1 and s in LETTERS else None


def normalise_label(raw):
    s = "" if raw is None else str(raw).strip().upper()
    return s if s in LABELS else UNLABELLED


def to_row(rec):
    """A Global-MMLU record (parquet columns) -> {sample_id, subject, category, options, key, label}."""
    return {"sample_id": rec.get("sample_id"), "subject": rec.get("subject"), "category": rec.get("subject_category"),
            "options": [rec.get(c) for c in OPTION_COLS], "key": key_index(rec.get("answer")),
            "label": normalise_label(rec.get("cultural_sensitivity_label"))}


def is_valid(options, key):
    """At least two options, none blank, and an integer key that indexes one of them."""
    if not isinstance(options, (list, tuple)) or len(options) < 2:
        return False
    if any(o is None or str(o).strip() == "" for o in options):
        return False
    return isinstance(key, int) and not isinstance(key, bool) and 0 <= key < len(options)


# ----- the length floor of a set of questions -----

def new_acc():
    return {"n": 0, "pl": Fraction(0), "ps": Fraction(0), "chance": Fraction(0), "d_sq": Fraction(0)}


def add(acc, options, gold):
    cl, cs = credits(options, gold)
    ch = Fraction(1, len(options))
    acc["n"] += 1
    acc["pl"] += cl
    acc["ps"] += cs
    acc["chance"] += ch
    acc["d_sq"] += (cl - ch) ** 2


def exact(acc):
    """(n, pick-longest, pick-shortest, chance) as exact fractions."""
    n = acc["n"]
    if not n:
        return 0, None, None, None
    return n, acc["pl"] / n, acc["ps"] / n, acc["chance"] / n


def floor_report(acc):
    """Same statistics as mcq-length-floor 0.1.0: lift = pick-longest - chance, se over questions, z = lift/se."""
    n = acc["n"]
    if not n:
        return {"n": 0}
    pl, ps, ch = acc["pl"] / n, acc["ps"] / n, acc["chance"] / n
    lift = pl - ch
    se = z = None
    if n > 1:
        var = (acc["d_sq"] - n * lift * lift) / (n - 1)
        se = math.sqrt(float(var) / n)
        z = float(lift) / se if se else None
    return {"n": n, "chance": float(ch), "pick_longest": float(pl), "pick_shortest": float(ps),
            "lift": float(lift), "ratio": float(pl / ch), "se": se, "z": z}


def census(rows):
    """rows: dicts with sample_id, subject, category, options, key, label (normalised). Valid rows only are
    accumulated. Returns {'n_rows', 'n_invalid', 'labels', 'accs': {slice: acc}, 'strata': {subject: (CS, CA)}}.
    Slices: ALL, label=<l>, cat=<category>, label=<l>|cat=<category>."""
    out = {"n_rows": 0, "n_invalid": 0, "labels": {}, "accs": {}, "strata": {}}
    for r in rows:
        out["n_rows"] += 1
        lab = r["label"]
        out["labels"][lab] = out["labels"].get(lab, 0) + 1
        if not is_valid(r["options"], r["key"]):
            out["n_invalid"] += 1
            continue
        cat = r.get("category") or "unknown"
        for nm in ("ALL", "label=" + lab, "cat=" + cat, "label=%s|cat=%s" % (lab, cat)):
            add(out["accs"].setdefault(nm, new_acc()), r["options"], r["key"])
        if lab in LABELS:
            pair = out["strata"].setdefault(r["subject"], (new_acc(), new_acc()))
            add(pair[LABELS.index(lab)], r["options"], r["key"])
    return out


# ----- CS minus CA -----

def _lift_and_var(acc):
    """(n, lift, plug-in variance of credit-minus-chance with denominator n), exact."""
    n = acc["n"]
    lift = (acc["pl"] - acc["chance"]) / n
    return n, lift, acc["d_sq"] / n - lift * lift


def diff_report(acc1, acc2):
    """lift(1) - lift(2) with a two-sample se from each side's mcq-length-floor se; z = diff / se."""
    r1, r2 = floor_report(acc1), floor_report(acc2)
    out = {"n_1": r1["n"], "n_2": r2["n"], "diff": None, "se": None, "z": None, "exact": None}
    if not r1["n"] or not r2["n"]:
        return out
    d = (acc1["pl"] - acc1["chance"]) / acc1["n"] - (acc2["pl"] - acc2["chance"]) / acc2["n"]
    out.update({"lift_1": r1["lift"], "lift_2": r2["lift"], "diff": float(d), "exact": d})
    if r1["se"] is not None and r2["se"] is not None:
        se = math.sqrt(r1["se"] ** 2 + r2["se"] ** 2)
        out["se"] = se
        out["z"] = float(d) / se if se else None
    return out


def stratified_diff(strata):
    """strata: {name: (acc_1, acc_2)}. Strata with at least one question on each side are combined with weights
    w = n1 n2 / (n1 + n2) on lift_1 - lift_2; the se uses plug-in (denominator n) variances."""
    num = den = var = Fraction(0)
    used = 0
    for name in sorted(strata):
        a1, a2 = strata[name]
        if not a1["n"] or not a2["n"]:
            continue
        n1, l1, v1 = _lift_and_var(a1)
        n2, l2, v2 = _lift_and_var(a2)
        w = Fraction(n1 * n2, n1 + n2)
        num += w * (l1 - l2)
        den += w
        var += w * w * (v1 / n1 + v2 / n2)
        used += 1
    if not den:
        return {"n_strata_used": 0, "estimate": None, "se": None, "z": None, "exact": None}
    est = num / den
    se = math.sqrt(float(var)) / float(den)
    return {"n_strata_used": used, "estimate": float(est), "se": se, "z": (float(est) / se) if se else None,
            "exact": est}


# ----- languages against English, and English against MMLU -----

def build_reference(rows):
    """{sample_id: (key, unique longest index or None, label)} from the reference language's rows."""
    ref = {}
    for r in rows:
        ul = unique_longest(r["options"]) if is_valid(r["options"], r["key"]) else None
        ref[r["sample_id"]] = (r["key"], ul, r["label"])
    return ref


def relabel(rows, ref):
    """Copies of rows carrying the reference language's label for the same sample_id (own label if absent), so
    every language is split into the same CS and CA questions."""
    out = []
    for r in rows:
        got = ref.get(r["sample_id"])
        out.append(dict(r, label=got[2]) if got is not None else dict(r))
    return out


def compare_to_reference(ref, rows):
    """Counts of missing sample_ids, key and label disagreements, and how often the reference's unique longest
    option is still the unique longest one here (over valid rows where the reference has one)."""
    out = {"n_rows": 0, "missing_in_reference": 0, "key_mismatch": 0, "label_mismatch": 0,
           "ref_unique_longest": 0, "same_unique_longest": 0}
    seen = set()
    for r in rows:
        out["n_rows"] += 1
        got = ref.get(r["sample_id"])
        if got is None:
            out["missing_in_reference"] += 1
            continue
        seen.add(r["sample_id"])
        rk, rul, rlab = got
        if r["key"] != rk:
            out["key_mismatch"] += 1
        if r["label"] != rlab:
            out["label_mismatch"] += 1
        if rul is not None and is_valid(r["options"], r["key"]):
            out["ref_unique_longest"] += 1
            if unique_longest(r["options"]) == rul:
                out["same_unique_longest"] += 1
    out["reference_ids_absent"] = len(set(ref) - seen)
    return out


def _s(o):
    return "" if o is None else str(o).strip()


def _indexes(k, seq):
    return isinstance(k, int) and not isinstance(k, bool) and 0 <= k < len(seq)


def mmlu_index(mmlu_rows):
    """MMLU test rows (subject, options, key) in file order -> {'<subject>/test/<i>': row}, i counted per subject."""
    idx, counter = {}, {}
    for r in mmlu_rows:
        i = counter.get(r["subject"], 0)
        counter[r["subject"]] = i + 1
        idx["%s/test/%d" % (r["subject"], i)] = r
    return idx


def compare_to_mmlu(rows, mmlu_rows):
    """Join rows to MMLU test by sample_id; count identical option lists, identical option sets, identical keys,
    identical key text, and rows identical in both options and key."""
    idx = mmlu_index(mmlu_rows)
    out = {"n_rows": 0, "joined": 0, "not_found": 0, "options_equal": 0, "same_option_set": 0, "key_equal": 0,
           "key_text_equal": 0, "all_equal": 0}
    seen = set()
    for r in rows:
        out["n_rows"] += 1
        m = idx.get(r["sample_id"])
        if m is None:
            out["not_found"] += 1
            continue
        out["joined"] += 1
        seen.add(r["sample_id"])
        a = [_s(o) for o in (r["options"] or [])]
        b = [_s(o) for o in (m["options"] or [])]
        oe = a == b
        ke = r["key"] is not None and r["key"] == m["key"]
        out["options_equal"] += int(oe)
        out["same_option_set"] += int(sorted(a) == sorted(b))
        out["key_equal"] += int(ke)
        out["key_text_equal"] += int(_indexes(r["key"], a) and _indexes(m["key"], b) and a[r["key"]] == b[m["key"]])
        out["all_equal"] += int(oe and ke)
    out["mmlu_unjoined"] = len(idx) - len(seen)
    return out
