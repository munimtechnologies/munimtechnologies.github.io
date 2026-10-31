"""MMLU-Redux LENGTH x ANNOTATION-ERROR census (audit 69).

Audits 52 and 60 found that MMLU carries a small "pick the longest option" shortcut (0.2805 vs 0.25 chance pooled,
near 50% in international law). MMLU-Redux 2.0 (Gema et al. 2024, arXiv 2406.04127; CC BY 4.0) re-annotated 100
questions from each of MMLU's 57 subjects with an expert error label and, for wrong-ground-truth questions, the
answer the experts think is right (`correct_answer`). This module joins the two lenses:

- the length floor (tie-aware pick-longest / pick-shortest accuracy vs chance) per error label, and on the
  expert-OK subset that leaderboards now report as "MMLU-Redux";
- on miskeyed questions, whether the length cue points to the expert-corrected answer or to the published key
  (paired: the same options scored against both keys);
- whether a question-free length flag ("the key is the unique shortest option", "another option is the unique
  longest") picks out miskeyed questions, pooled and stratified by subject (Cochran-Mantel-Haenszel).

Lengths are characters after stripping, exactly as in mcq-length-floor 0.1.0. Standard library only. Apache-2.0.
Authored by AI agents working in the name of MV2, Munim, Inc.
"""

import math
import re
from fractions import Fraction

OK = "ok"
UNSURE = "expert"
ERROR_TYPES = ("bad_question_clarity", "bad_options_clarity", "no_correct_answer", "multiple_correct_answers",
               "wrong_groundtruth")
JUDGED = (OK,) + ERROR_TYPES
MISKEY = "wrong_groundtruth"

LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
SPLIT_RE = re.compile(r"\s*(?:,|;|/|&|\band\b)\s*")
LETTER_RE = re.compile(r"^\(?([A-Z])\)?\.?$")
DIGIT_RE = re.compile(r"^[0-9]$")

CHI2_CRIT_1DF_005 = 3.841
CHI2_CRIT_1DF_0001 = 10.828
Z_CRIT_0001 = 3.29


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


def length_rank(options, idx):
    """Normalised length rank of option idx: (shorter others + half the tied others) / (k - 1).
    0 = strictly the shortest, 1 = strictly the longest, 0.5 = no lean."""
    L = [length(o) for o in options]
    others = [x for j, x in enumerate(L) if j != idx]
    s = sum(1 for x in others if x < L[idx]) + Fraction(1, 2) * sum(1 for x in others if x == L[idx])
    return Fraction(s) / len(others)


def unique_longest(options):
    """Index of the unique longest option, or None when the longest length is tied."""
    L = [length(o) for o in options]
    hi = max(L)
    return L.index(hi) if L.count(hi) == 1 else None


def unique_shortest(options):
    L = [length(o) for o in options]
    lo = min(L)
    return L.index(lo) if L.count(lo) == 1 else None


def is_valid(options, key):
    """At least two options, none blank, and an integer key that indexes one of them."""
    if not isinstance(options, (list, tuple)) or len(options) < 2:
        return False
    if any(o is None or str(o).strip() == "" for o in options):
        return False
    return isinstance(key, int) and not isinstance(key, bool) and 0 <= key < len(options)


def normalise_label(error_type):
    return "" if error_type is None else str(error_type).strip().lower()


def error_class(label):
    if label == OK:
        return "ok"
    if label in ERROR_TYPES:
        return "error"
    if label == UNSURE:
        return "unsure"
    return "unknown"


# ----- the experts' suggested answer -----

def parse_correction(raw, options):
    """correct_answer -> (format, indices). Formats, tried in order: 'none' (null/empty); 'letters' (one or more
    capital letters, each indexing an option, separated by , ; / & or 'and'); 'text' (equals exactly one option's
    text, ignoring case and outer spaces); 'digits' (one or more single digits, 0..k -- 0- or 1-based is not
    documented, so these stay unresolved unless a base is chosen); otherwise 'unmatched'."""
    if raw is None or str(raw).strip() == "":
        return "none", ()
    s = str(raw).strip()
    k = len(options)
    tokens = [t for t in SPLIT_RE.split(s) if t != ""]
    letters = [LETTER_RE.match(t) for t in tokens]
    if tokens and all(letters):
        idx = tuple(LETTERS.index(m.group(1)) for m in letters)
        if all(i < k for i in idx):
            return "letters", idx
    hits = [i for i, o in enumerate(options) if str(o).strip().casefold() == s.casefold()]
    if len(hits) == 1:
        return "text", (hits[0],)
    if tokens and all(DIGIT_RE.match(t) for t in tokens) and all(int(t) <= k for t in tokens):
        return "digits", tuple(int(t) for t in tokens)
    return "unmatched", ()


def resolve(fmt, idx, k, digit_base=None):
    """Indices of the suggested answer, or None if unresolved (digits need digit_base 0 or 1)."""
    if fmt in ("letters", "text"):
        return idx
    if fmt == "digits" and digit_base in (0, 1):
        out = tuple(i - digit_base for i in idx)
        return out if all(0 <= i < k for i in out) else None
    return None


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
    """rows: dicts with subject, options, key, label (normalised). Valid rows only are accumulated.
    Returns {'n_rows', 'n_invalid', 'labels', 'subjects', 'accs': {slice: acc}}. Slices: ALL, class=<c>,
    label=<l>, and ok|subject=<s> (the expert-OK floor per subject)."""
    out = {"n_rows": 0, "n_invalid": 0, "labels": {}, "subjects": {}, "accs": {}}
    for r in rows:
        out["n_rows"] += 1
        lab = r["label"]
        out["labels"][lab] = out["labels"].get(lab, 0) + 1
        out["subjects"][r["subject"]] = out["subjects"].get(r["subject"], 0) + 1
        if not is_valid(r["options"], r["key"]):
            out["n_invalid"] += 1
            continue
        names = ["ALL", "class=" + error_class(lab), "label=" + lab]
        if lab == OK:
            names.append("ok|subject=" + r["subject"])
        for nm in names:
            add(out["accs"].setdefault(nm, new_acc()), r["options"], r["key"])
    return out


# ----- miskeyed questions: published key vs expert-corrected key -----

def miskey_pairs(rows, digit_base=None, exclude_subjects=()):
    """(options, key, corrected) for valid wrong-ground-truth rows whose suggestion resolves to exactly ONE option
    different from the key, plus counts of why the others were left out."""
    pairs, why = [], {}
    for r in rows:
        if r["label"] != MISKEY or r["subject"] in exclude_subjects:
            continue
        if not is_valid(r["options"], r["key"]):
            why["invalid"] = why.get("invalid", 0) + 1
            continue
        fmt, idx = parse_correction(r.get("correct"), r["options"])
        res = resolve(fmt, idx, len(r["options"]), digit_base)
        if res is None:
            reason = "unresolved_" + fmt
        elif len(res) != 1:
            reason = "several_suggested"
        elif res[0] == r["key"]:
            reason = "same_as_key"
        else:
            pairs.append((r["options"], r["key"], res[0]))
            continue
        why[reason] = why.get(reason, 0) + 1
    return pairs, why


def _mean_se(sum_x, sum_sq, n):
    mean = sum_x / n
    if n < 2:
        return mean, None
    var = (sum_sq - n * mean * mean) / (n - 1)
    return mean, math.sqrt(float(var) / n)


def paired(pairs):
    """Exact sums and summary for pick-longest credit and length rank under the published vs corrected key."""
    s = {"n": 0, "pl_orig": Fraction(0), "pl_corr": Fraction(0), "d": Fraction(0), "d_sq": Fraction(0),
         "rank_orig": Fraction(0), "rank_corr": Fraction(0), "dr": Fraction(0), "dr_sq": Fraction(0),
         "ul_orig": 0, "ul_corr": 0, "us_orig": 0, "us_corr": 0}
    for options, key, corr in pairs:
        co, _ = credits(options, key)
        cc, _ = credits(options, corr)
        ro, rc = length_rank(options, key), length_rank(options, corr)
        ul, us = unique_longest(options), unique_shortest(options)
        s["n"] += 1
        s["pl_orig"] += co
        s["pl_corr"] += cc
        s["d"] += cc - co
        s["d_sq"] += (cc - co) ** 2
        s["rank_orig"] += ro
        s["rank_corr"] += rc
        s["dr"] += rc - ro
        s["dr_sq"] += (rc - ro) ** 2
        s["ul_orig"] += int(ul == key)
        s["ul_corr"] += int(ul == corr)
        s["us_orig"] += int(us == key)
        s["us_corr"] += int(us == corr)
    return s


def paired_report(s):
    n = s["n"]
    if not n:
        return {"n": 0}
    d, d_se = _mean_se(s["d"], s["d_sq"], n)
    dr, dr_se = _mean_se(s["dr"], s["dr_sq"], n)
    return {
        "n": n,
        "pick_longest_vs_published_key": float(s["pl_orig"] / n),
        "pick_longest_vs_corrected_key": float(s["pl_corr"] / n),
        "mean_diff": float(d), "diff_se": d_se, "diff_z": (float(d) / d_se) if d_se else None,
        "length_rank_published_key": float(s["rank_orig"] / n),
        "length_rank_corrected_key": float(s["rank_corr"] / n),
        "rank_diff": float(dr), "rank_diff_se": dr_se, "rank_diff_z": (float(dr) / dr_se) if dr_se else None,
        "published_key_unique_longest": s["ul_orig"], "corrected_key_unique_longest": s["ul_corr"],
        "published_key_unique_shortest": s["us_orig"], "corrected_key_unique_shortest": s["us_corr"],
    }


# ----- question-free length flags as miskey detectors -----

def flag_key_unique_shortest(options, key):
    return unique_shortest(options) == key


def flag_other_unique_longest(options, key):
    ul = unique_longest(options)
    return ul is not None and ul != key


FLAGS = {"key_is_unique_shortest": flag_key_unique_shortest,
         "another_option_is_unique_longest": flag_other_unique_longest}


def two_by_two(a, b, c, d):
    """Pearson chi-square (df 1, no continuity correction) for [[a, b], [c, d]]; row 1 rate a/(a+b) vs c/(c+d)."""
    n = a + b + c + d
    r1, r2, c1, c2 = a + b, c + d, a + c, b + d
    rate1 = (a / r1) if r1 else None
    rate2 = (c / r2) if r2 else None
    if n and r1 and r2 and c1 and c2:
        stat = n * (a * d - b * c) ** 2 / (r1 * r2 * c1 * c2)
        min_exp = min(r1, r2) * min(c1, c2) / n
    else:
        stat = None
        min_exp = None
    return {
        "table": [[a, b], [c, d]],
        "rate_1": rate1,
        "rate_2": rate2,
        "risk_ratio": (rate1 / rate2) if (rate1 is not None and rate2) else None,
        "chi_square_stat": stat,
        "df": 1,
        "min_expected_cell": min_exp,
        "rejected_0.05": (stat > CHI2_CRIT_1DF_005) if stat is not None else None,
        "rejected_0.001": (stat > CHI2_CRIT_1DF_0001) if stat is not None else None,
    }


def cmh(strata):
    """Cochran-Mantel-Haenszel test over 2x2 strata (a, b, c, d), no continuity correction, df 1 (as audit 58)."""
    num = 0.0
    var = 0.0
    or_n = 0.0
    or_d = 0.0
    n_inf = 0
    for a, b, c, d in strata:
        n = a + b + c + d
        if n < 2:
            continue
        r1, r2, c1, c2 = a + b, c + d, a + c, b + d
        num += a - r1 * c1 / n
        v = r1 * r2 * c1 * c2 / (n * n * (n - 1))
        var += v
        or_n += a * d / n
        or_d += b * c / n
        if v > 0:
            n_inf += 1
    stat = (num * num / var) if var > 0 else None
    return {
        "n_strata": len(strata),
        "n_informative_strata": n_inf,
        "sum_observed_minus_expected": num,
        "sum_variance": var,
        "cmh_stat": stat,
        "df": 1,
        "mh_odds_ratio": (or_n / or_d) if or_d > 0 else None,
        "mh_or_numerator": or_n,
        "mh_or_denominator": or_d,
        "rejected_0.05": (stat > CHI2_CRIT_1DF_005) if stat is not None else None,
        "rejected_0.001": (stat > CHI2_CRIT_1DF_0001) if stat is not None else None,
    }


def detector(rows, flag, targets):
    """Among valid JUDGED rows (ok + the five error types): flagged vs not, against label in targets.
    Returns {'pooled': two_by_two, 'by_subject_cmh': cmh, 'strata': {subject: [a, b, c, d]}}."""
    strata = {}
    for r in rows:
        if r["label"] not in JUDGED or not is_valid(r["options"], r["key"]):
            continue
        cell = strata.setdefault(r["subject"], [0, 0, 0, 0])
        f = flag(r["options"], r["key"])
        t = r["label"] in targets
        cell[(0 if f else 2) + (0 if t else 1)] += 1
    a, b, c, d = (sum(s[i] for s in strata.values()) for i in range(4))
    order = sorted(strata)
    return {"pooled": two_by_two(a, b, c, d), "by_subject_cmh": cmh([tuple(strata[s]) for s in order]),
            "strata": {s: strata[s] for s in order}}


def correction_formats(rows):
    """Counts of correct_answer formats per label (labels with at least one non-null suggestion)."""
    out = {}
    for r in rows:
        if not is_valid(r["options"], r["key"]):
            continue
        fmt, _ = parse_correction(r.get("correct"), r["options"])
        c = out.setdefault(r["label"], {})
        c[fmt] = c.get(fmt, 0) + 1
    return {lab: dict(sorted(c.items())) for lab, c in sorted(out.items()) if set(c) != {"none"}}
