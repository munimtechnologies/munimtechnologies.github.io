"""Do models pick the experts' answer on MMLU-Pro's inherited MMLU miskeys? Core logic for audit 76.

Audit 75 joined MMLU-Redux 2.0's expert labels to MMLU-Pro and found 52 MMLU-Pro questions that still carry the MMLU
key Redux's experts marked wrong ("wrong_groundtruth"). On 46 of them the experts' answer resolves to one of
MMLU-Pro's options (24 from a letter or exact-text correction, 22 from a digit correction read 0-based, the reading
audit 75 found to be the only coherent one). This module classifies each published model prediction on those 46
questions as the published KEY, the EXPERTS' answer, another option (OTHER) or no valid answer (NONE), and compares
the experts' option with an average other distractor and with each model's accuracy elsewhere.

Standard library only. Apache-2.0. Authored by AI agents working in the name of MV2, Munim, Inc.
"""

from fractions import Fraction

LETTERS = "ABCDEFGHIJ"
CLASSES = ("key", "expert", "other", "none")


def pred_index(pred, k):
    """Index of a predicted letter A-J within k options, or None when missing / malformed / out of range
    (the same rule as audits 65/66)."""
    if not isinstance(pred, str):
        return None
    p = pred.strip().upper()
    if len(p) != 1 or p not in LETTERS:
        return None
    i = LETTERS.index(p)
    return i if i < k else None


def classify(pred, key_i, exp_i, k):
    """'key' | 'expert' | 'other' | 'none' for one prediction on a question with k options."""
    i = pred_index(pred, k)
    if i is None:
        return "none"
    if i == key_i:
        return "key"
    if i == exp_i:
        return "expert"
    return "other"


def new_tally():
    return {"n": 0, "key": 0, "expert": 0, "other": 0, "none": 0, "other_per_distractor": Fraction(0)}


def add_tally(t, cls, k):
    """One classified prediction. An OTHER pick adds 1/(k-2): the share of one average other distractor, so
    'other_per_distractor' is directly comparable with the 'expert' count (one specific option)."""
    t["n"] += 1
    t[cls] += 1
    if cls == "other":
        t["other_per_distractor"] += Fraction(1, k - 2)


def merge(a, b):
    out = new_tally()
    for f in out:
        out[f] = a[f] + b[f]
    return out


def tally_report(t):
    n = t["n"]
    opd = t["other_per_distractor"]
    return {"n": n, "key": t["key"], "expert": t["expert"], "other": t["other"], "none": t["none"],
            "key_rate": (t["key"] / n) if n else None,
            "expert_rate": (t["expert"] / n) if n else None,
            "other_per_distractor": float(opd),
            "expert_vs_average_distractor": (float(Fraction(t["expert"]) / opd)) if opd > 0 else None}


def new_ctrl():
    return {"n": 0, "correct": 0}


def add_ctrl(c, pred, gold, k):
    """Control accuracy as MMLU-Pro scores it; a missing or malformed prediction counts as not correct."""
    c["n"] += 1
    i = pred_index(pred, k)
    c["correct"] += 1 if (i is not None and i == gold) else 0


def ctrl_accuracy(c):
    return (c["correct"] / c["n"]) if c["n"] else None


def predictions(models, per_question, min_targets, thresholds):
    """models: {name: {"all": tally, "primary": tally, "control_accuracy": float}} for included models.
    per_question: {qid: tally pooled over included models}. Returns the pre-registered verdicts P2-P7 (P1 is the
    structural gate, decided in job.py) with their counts."""
    pooled = new_tally()
    pooled_primary = new_tally()
    for m in models.values():
        pooled = merge(pooled, m["all"])
        pooled_primary = merge(pooled_primary, m["primary"])
    eligible = sorted(n for n, m in models.items() if m["all"]["n"] >= min_targets)
    exp_over_key = [n for n in eligible if models[n]["all"]["expert"] > models[n]["all"]["key"]]
    below_ctrl = [n for n in eligible
                  if models[n]["control_accuracy"] is not None
                  and models[n]["all"]["key"] / models[n]["all"]["n"] < models[n]["control_accuracy"]]
    answered = [q for q, t in per_question.items() if t["n"] > 0]
    q_exp_over_key = [q for q in answered if per_question[q]["expert"] > per_question[q]["key"]]
    out = {
        "P2_pooled_expert_over_key": pooled["expert"] > pooled["key"],
        "P2_counts": [pooled["expert"], pooled["key"]],
        "P3_most_models_expert_over_key": bool(eligible) and
        Fraction(len(exp_over_key), len(eligible)) >= thresholds["P3_share"],
        "P3_counts": [len(exp_over_key), len(eligible)],
        "P4_expert_vs_average_distractor": pooled["other_per_distractor"] > 0 and
        Fraction(pooled["expert"]) >= thresholds["P4_ratio"] * pooled["other_per_distractor"],
        "P4_counts": [pooled["expert"], float(pooled["other_per_distractor"])],
        "P5_key_rate_below_control_every_model": bool(eligible) and len(below_ctrl) == len(eligible),
        "P5_counts": [len(below_ctrl), len(eligible)],
        "P6_questions_expert_over_key": bool(answered) and
        Fraction(len(q_exp_over_key), len(answered)) >= thresholds["P6_share"],
        "P6_counts": [len(q_exp_over_key), len(answered)],
        "P7_primary_subset_expert_over_key": pooled_primary["expert"] > pooled_primary["key"],
        "P7_counts": [pooled_primary["expert"], pooled_primary["key"]],
    }
    return out, pooled, pooled_primary
