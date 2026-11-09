"""How much do HELM's MedCalc-Bench scoring gaps (#4351, #4365) change MedHELM's published scores? Core logic, audit 96.

HELM's MedCalcBenchMetric (src/helm/benchmark/metrics/medcalc_bench_metrics.py, transcribed below from
stanford-crfm/helm, Apache-2.0) scores one output per instance:
  * categories risk, severity, diagnosis: the stripped output must equal the reference string;
  * category date: a calendar date within [lower_limit, upper_limit] (format %m/%d/%Y), or, when the reference is a
    duration "('W weeks', 'D days')", an output in exactly that quoted, plural form within the limits;
  * categories "dosage conversion" and physical: float(output) within [lower_limit, upper_limit];
  * any other category raises ValueError inside the try block and scores 0. MedCalc-Bench's categories are lab and
    dosage, so (HELM issue #4351) every lab and dosage instance scores 0.

Graders applied to every archived first-trial prediction:
  H  HELM's score, transcribed and gated against HELM's recorded medcalc_bench_accuracy;
  R  H plus #4351's fix: lab and dosage are range-checked like physical;
  C  the corrected grade: R plus a duration rule (an unquoted or singular tuple such as "(18, 1)" or
     "(18 weeks, 1 day)" counts when its total days are within the limits; cf. #4365) plus a same-value rule for
     risk, severity and diagnosis (an output that is a number equal in value to a numeric reference, e.g. "9.0" for
     "9"). C never lowers a grade: it credits only predictions H scores 0.
Standard library only. Apache-2.0. Authored by AI agents working in the name of MV2, Munim, Inc.
"""

import math
import re
from datetime import datetime

EXACT_CATEGORIES = ("risk", "severity", "diagnosis")
RANGE_CATEGORIES = ("lab", "dosage", "physical")
HELM_DURATION = r"\('(\d+) weeks', '(\d+) days'\)"

# ----- HELM's MedCalcBenchMetric, transcribed -----


def parse_duration(duration_str):
    match = re.match(HELM_DURATION, duration_str)
    if match:
        weeks, days = map(int, match.groups())
        return weeks * 7 + days
    raise ValueError("Invalid format: %s" % duration_str)


def is_within_range(lower_bound, upper_bound, prediction):
    lower_days = parse_duration(lower_bound)
    upper_days = parse_duration(upper_bound)
    prediction_days = parse_duration(prediction)
    return 1 if lower_days <= prediction_days <= upper_days else 0


def _str_to_date(date_str):
    return datetime.strptime(date_str, "%m/%d/%Y")


def check_date(prediction, reference, extra):
    if re.match(HELM_DURATION, reference):
        return is_within_range(extra["lower_limit"], extra["upper_limit"], prediction)
    prediction_date = _str_to_date(prediction)
    upper_limit_date = _str_to_date(extra["upper_limit"])
    lower_limit_date = _str_to_date(extra["lower_limit"])
    return 1 if lower_limit_date <= prediction_date <= upper_limit_date else 0


def check_in_range(prediction, reference, extra, category):
    try:
        if category == "date":
            exact_match = check_date(prediction, reference, extra)
        elif category in ["dosage conversion", "physical"]:
            lower_limit = float(extra["lower_limit"])
            upper_limit = float(extra["upper_limit"])
            float_prediction = float(prediction)
            exact_match = 1 if lower_limit <= float_prediction <= upper_limit else 0
        else:
            raise ValueError("Category %s not supported" % category)
    except ValueError:
        return 0
    return exact_match


def helm_score(predicted_text, reference, extra, category):
    """HELM's medcalc_bench_accuracy for one output (evaluate_generation: the first completion, stripped)."""
    prediction = (predicted_text or "").strip()
    if category in EXACT_CATEGORIES:
        return 1 if prediction == reference else 0
    return check_in_range(prediction, reference, extra, category)


# ----- The corrections -----

# A whole-string (weeks, days) tuple: optional matching quotes around each part, optional singular or plural labels
# (both parts labelled or neither).
DURATION_ANY = re.compile(r"""^\(\s*(['"]?)\s*(\d+)\s*(weeks?)?\s*\1\s*,\s*(['"]?)\s*(\d+)\s*(days?)?\s*\4\s*\)$""")


def plain_number(text):
    """float(text.strip()) when it is a finite number, else None."""
    try:
        v = float((text or "").strip())
    except ValueError:
        return None
    return v if math.isfinite(v) else None


def range_credit(predicted_text, extra):
    """#4351's fix: the output as a number within [lower_limit, upper_limit] (as HELM checks physical)."""
    v = plain_number(predicted_text)
    if v is None:
        return 0
    try:
        lo, hi = float(extra["lower_limit"]), float(extra["upper_limit"])
    except (ValueError, KeyError, TypeError):
        return 0
    return 1 if lo <= v <= hi else 0


def duration_days(predicted_text):
    """Total days of a whole-string (weeks, days) tuple in any accepted form, else None."""
    m = DURATION_ANY.match((predicted_text or "").strip())
    if not m or (m.group(3) is None) != (m.group(6) is None):
        return None
    return int(m.group(2)) * 7 + int(m.group(5))


def duration_credit(predicted_text, reference, extra):
    if not re.match(HELM_DURATION, reference or ""):
        return 0
    d = duration_days(predicted_text)
    if d is None:
        return 0
    try:
        lo, hi = parse_duration(extra["lower_limit"]), parse_duration(extra["upper_limit"])
    except (ValueError, KeyError, TypeError):
        return 0
    return 1 if lo <= d <= hi else 0


def same_value(predicted_text, reference):
    """1 when output and reference are both plain numbers of equal value ('9.0' and '9')."""
    p, r = plain_number(predicted_text), plain_number(reference)
    return 1 if p is not None and r is not None and p == r else 0


def rounded_only(predicted_text, reference):
    """Exploratory (not in C): the benchmark authors' integer rule, round(output) == an integer reference, where the
    values differ before rounding."""
    p, r = plain_number(predicted_text), plain_number(reference)
    if p is None or r is None or r != int(r) or p == r:
        return 0
    return 1 if round(p) == r else 0


def grade(predicted_text, reference, extra, category):
    """H, R and C for one output, and the class of an up-flip (C 1, H 0): 'range_lab', 'range_dosage',
    'duration_format' or 'same_value'."""
    h = helm_score(predicted_text, reference, extra, category)
    r, c, cls = h, h, None
    if h == 0:
        if category in ("lab", "dosage") and range_credit(predicted_text, extra):
            r, c, cls = 1, 1, "range_" + category
        elif category == "date" and duration_credit(predicted_text, reference, extra):
            c, cls = 1, "duration_format"
        elif category in EXACT_CATEGORIES and same_value(predicted_text, reference):
            c, cls = 1, "same_value"
    return {"h": h, "r": r, "c": c, "cls": cls}


# ----- Ranks and rank agreement (copied unchanged from audit 92, grade92.py) -----

def min_ranks(acc):
    """acc {model: Fraction} -> {model: 1 + number of models with a strictly higher accuracy}."""
    return {m: 1 + sum(1 for o in acc if acc[o] > acc[m]) for m in acc}


def kendall_tau_b(xs, ys):
    """Kendall's tau-b of two equal-length lists; None when either list is constant."""
    conc = disc = tx = ty = 0
    n = len(xs)
    for i in range(n):
        for j in range(i + 1, n):
            dx = (xs[i] > xs[j]) - (xs[i] < xs[j])
            dy = (ys[i] > ys[j]) - (ys[i] < ys[j])
            if dx == 0 and dy == 0:
                continue
            if dx == 0:
                tx += 1
            elif dy == 0:
                ty += 1
            elif dx == dy:
                conc += 1
            else:
                disc += 1
    denom = ((conc + disc + tx) * (conc + disc + ty)) ** 0.5
    return (conc - disc) / denom if denom else None


# ----- Run selection (copied unchanged from audit 92, grade92.py) -----

def _version(s):
    out = []
    for p in (s or "").lstrip("v").split("."):
        try:
            out.append(int(p))
        except ValueError:
            out.append(-1)
    return tuple(out)


def run_part(run, key):
    """'mmlu:subject=x,method=y,model=a_b' -> value of `key` (None if absent)."""
    body = run.split(":", 1)[1] if ":" in run else run
    for part in body.split(","):
        if part.startswith(key + "="):
            return part[len(key) + 1:]
    return None


def select_runs(run_suites, prefix, must_contain=None):
    """One run per (model, subject) among keys starting with `prefix` (and containing `must_contain`, if given);
    subject '-' when the run has none. The newest suite wins, then the shortest and alphabetically first key.
    Returns ({(model, subject): (run, suite)}, runs dropped as duplicates)."""
    best, dropped = {}, 0
    for run, suite in run_suites.items():
        if not run.startswith(prefix):
            continue
        if must_contain is not None and must_contain not in run:
            continue
        m = run_part(run, "model")
        if m is None:
            continue
        s = run_part(run, "subject") or "-"
        k, cand = (m, s), (run, suite)
        if k in best:
            dropped += 1
            cur = best[k]
            if (_version(suite), -len(run), [-ord(c) for c in run]) > (_version(cur[1]), -len(cur[0]),
                                                                           [-ord(c) for c in cur[0]]):
                best[k] = cand
        else:
            best[k] = cand
    return best, dropped


# ----- Pre-registered verdicts P2-P7 (P1 is decided in job.py) -----

def predictions96(h_lab_dosage, gains_r, n_duration, n_same_value, n_exact, n_rank_changed, n_models_format, th):
    """h_lab_dosage: lab and dosage predictions H credits (all included runs); gains_r: per-model accuracy gains
    R - H (Fractions); n_duration / n_same_value: up-flips of class duration_format / same_value; n_exact: included
    risk, severity and diagnosis predictions; n_rank_changed: models whose rank differs between H and C;
    n_models_format: models with at least th['P7_share'] of their lab, dosage and physical outputs not a plain
    number."""
    mean_gain = sum(gains_r) / len(gains_r) if gains_r else None
    return {
        "P2_lab_dosage_zero": h_lab_dosage == 0,
        "P3_range_fix_size": bool(gains_r and mean_gain >= th["P3_mean"] and min(gains_r) >= th["P3_min"]),
        "P4_duration_replicates": th["P4_lo"] <= n_duration <= th["P4_hi"],
        "P5_same_value_rare": bool(n_exact > 0 and n_same_value * th["P5_den"] < n_exact * th["P5_num"]),
        "P6_ranks_change": n_rank_changed >= th["P6_min"],
        "P7_format_loss": n_models_format >= th["P7_min"],
    }
