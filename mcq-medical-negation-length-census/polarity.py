"""Does the answer-length shortcut flip on NOT / EXCEPT questions? Core logic for audit 68.

Audits 51-64 measured a question-free "pick the longest option" heuristic across multiple-choice benchmarks (18.4%
pooled on MMLU-Pro against 11.1% chance). Exam writers are known to qualify the correct statement until it is fully
true, which makes it long. In a negatively worded question ("All of the following are true EXCEPT") the keyed answer
is the false statement, so that habit should stop helping and may even reverse. This module measures, per dataset,
split, stem polarity and subject:

- the tie-aware accuracy of picking the longest option and of picking the shortest option;
- the exact variable-k chance baseline and the lift over it, with a standard error over questions;
- the share of questions carrying an "all / none / both of the above" style option.

Stem polarity is read from the LAST sentence of the question only, so negations inside a clinical vignette ("the
patient does not smoke") do not count. Lengths are Unicode code points after str.strip(). Standard library only.
Apache-2.0.
"""

import math
import re
from fractions import Fraction

NEG_RE = re.compile(r"\b(not|except|false|incorrect|untrue|least)\b|n['’]t\b", re.IGNORECASE)
SENT_SPLIT = re.compile(r"(?<=[.?!])\s+")
META_FIRST = ("all", "none", "both", "neither")
META_MAX_WORDS = 6

MIN_NEG = 30            # P3 / P8 contrasts are scored only when both polarities have at least this many questions
P2_TOL = 0.05
P5_SHARE = 0.5
P7_MIN_N = 1000
P7_SHARE = 0.8
DATASETS = ("mmlu_pro", "medmcqa", "medqa")


def lens(options):
    return [len(str(o).strip()) for o in options]


def longest_credit(options, gold):
    """Tie-aware expected credit of 'pick the longest option' (same rule as audits 61-67)."""
    L = lens(options)
    m = max(L)
    return Fraction(1, L.count(m)) if L[gold] == m else Fraction(0)


def shortest_credit(options, gold):
    """Tie-aware expected credit of 'pick the shortest option'."""
    L = lens(options)
    m = min(L)
    return Fraction(1, L.count(m)) if L[gold] == m else Fraction(0)


def last_sentence(question):
    """The final sentence of a question stem (split after . ? ! followed by whitespace)."""
    s = str(question or "").strip()
    parts = [p for p in SENT_SPLIT.split(s) if p.strip()]
    return parts[-1] if parts else ""


def polarity(question):
    """'neg' when the last sentence holds not / except / false / incorrect / untrue / least / n't, else 'pos'."""
    return "neg" if NEG_RE.search(last_sentence(question)) else "pos"


def is_meta(option):
    """An 'all of the above' / 'none' / 'both 1 and 2' style option: first word all|none|both|neither, <= 6 words."""
    words = re.sub(r"[^a-z0-9 ]", " ", str(option).lower()).split()
    return bool(words) and words[0] in META_FIRST and len(words) <= META_MAX_WORDS


def family(src):
    """MMLU-Pro source family: the src prefix before the first '-' (e.g. 'stemez-Biology' -> 'stemez')."""
    s = src or ""
    return s.split("-", 1)[0] if s else "unknown"


def new_acc():
    return {"n": 0, "pl": Fraction(0), "ps": Fraction(0), "chance": Fraction(0), "d_sq": Fraction(0),
            "n_meta": 0, "n_ul": 0, "gold_ul": 0}


def add(acc, options, gold):
    L = lens(options)
    k = len(L)
    c = longest_credit(options, gold)
    ch = Fraction(1, k)
    d = c - ch
    acc["n"] += 1
    acc["pl"] += c
    acc["ps"] += shortest_credit(options, gold)
    acc["chance"] += ch
    acc["d_sq"] += d * d
    if any(is_meta(o) for o in options):
        acc["n_meta"] += 1
    m = max(L)
    if L.count(m) == 1:
        acc["n_ul"] += 1
        if L[gold] == m:
            acc["gold_ul"] += 1


def keys_for(row):
    """Accumulator keys for one normalised row {dataset, split, question, options, gold, groups}."""
    d = row["dataset"]
    p = "pol=" + polarity(row["question"])
    s = "split=" + row["split"]
    out = [d + "|ALL", d + "|" + p, d + "|" + s, d + "|" + s + "|" + p]
    if not any(is_meta(o) for o in row["options"]):
        out.append(d + "|nometa|" + p)
    for g in row["groups"]:
        out += [d + "|" + g, d + "|" + g + "|" + p]
    return out


def accumulate(rows):
    accs = {}
    for r in rows:
        for key in keys_for(r):
            add(accs.setdefault(key, new_acc()), r["options"], r["gold"])
    return accs


def report(acc):
    n = acc["n"]
    if not n:
        return {"n": 0}
    pl = acc["pl"] / n
    ps = acc["ps"] / n
    ch = acc["chance"] / n
    lift = pl - ch
    se = None
    if n > 1:
        var = (acc["d_sq"] - n * lift * lift) / (n - 1)
        se = math.sqrt(float(var) / n)
    return {
        "n": n,
        "pick_longest": float(pl),
        "pick_shortest": float(ps),
        "chance": float(ch),
        "lift": float(lift),
        "shortest_lift": float(ps - ch),
        "ratio": float(pl / ch),
        "se_lift": se,
        "meta_share": acc["n_meta"] / n,
        "unique_longest_share": acc["n_ul"] / n,
        "gold_given_unique_longest": acc["gold_ul"] / acc["n_ul"] if acc["n_ul"] else None,
    }


def contrast(neg, pos):
    """Negative-stem lift minus positive-stem lift, with a two-sample z on the per-question lifts."""
    if not neg.get("n") or not pos.get("n"):
        return {"lift_diff": None, "z": None}
    diff = neg["lift"] - pos["lift"]
    z = None
    if neg.get("se_lift") is not None and pos.get("se_lift") is not None:
        den = math.sqrt(neg["se_lift"] ** 2 + pos["se_lift"] ** 2)
        z = diff / den if den else None
    return {"lift_diff": diff, "z": z, "n_neg": neg["n"], "n_pos": pos["n"]}


def _r(reports, key):
    return reports.get(key, {})


def _lift(reports, key):
    return _r(reports, key).get("lift")


def predictions(reports):
    """Pre-registered predictions, written before any count on the medical files was computed."""
    def pair(prefix):
        neg, pos = _r(reports, prefix + "|pol=neg"), _r(reports, prefix + "|pol=pos")
        ok = neg.get("n", 0) >= MIN_NEG and pos.get("n", 0) >= MIN_NEG
        return ok, neg, pos

    # P1: on MedMCQA's validation split (the one medical LLM papers report) pick-longest beats chance.
    v = _lift(reports, "medmcqa|split=validation")
    p1 = v is not None and v > 0

    # P2: on MedQA-USMLE's test split pick-longest stays within 5 points of chance (NBME-style item writing).
    t = _lift(reports, "medqa|split=test")
    p2 = t is not None and abs(t) <= P2_TOL

    # P3: in each of MMLU-Pro, MedMCQA and MedQA, negative stems give a lower pick-longest lift than positive stems.
    p3_detail = {}
    p3 = True
    for d in DATASETS:
        ok, neg, pos = pair(d)
        c = contrast(neg, pos)
        c["scored"] = ok
        p3_detail[d] = c
        p3 = p3 and ok and c["lift_diff"] is not None and c["lift_diff"] < 0

    # P4: on MedMCQA (train + validation) negative-stem questions, pick-longest scores BELOW chance (a reversal).
    mneg = _r(reports, "medmcqa|pol=neg")
    p4 = mneg.get("n", 0) >= MIN_NEG and mneg["lift"] < 0

    # P5: on MMLU-Pro the negative-stem lift is less than half the positive-stem lift.
    ok, neg, pos = pair("mmlu_pro")
    p5 = ok and pos["lift"] > 0 and neg["lift"] < P5_SHARE * pos["lift"]

    # P6: MedMCQA validation's lift is at least MedQA test's lift.
    p6 = v is not None and t is not None and v >= t

    # P7: pick-longest beats chance in at least 80% of MedMCQA subjects with >= 1000 questions.
    subj = {k.split("|", 1)[1][len("subject="):]: r for k, r in reports.items()
            if k.startswith("medmcqa|subject=") and "|pol=" not in k and r.get("n", 0) >= P7_MIN_N}
    wins = sorted(s for s, r in subj.items() if r["lift"] > 0)
    p7 = bool(subj) and len(wins) >= P7_SHARE * len(subj)

    # P8: the MedMCQA polarity contrast keeps its sign after dropping every question with an all/none/both option.
    neg8, pos8 = _r(reports, "medmcqa|nometa|pol=neg"), _r(reports, "medmcqa|nometa|pol=pos")
    c8 = contrast(neg8, pos8)
    p8 = (neg8.get("n", 0) >= MIN_NEG and pos8.get("n", 0) >= MIN_NEG
          and c8["lift_diff"] is not None and c8["lift_diff"] < 0)

    return {
        "P1_medmcqa_validation_beats_chance": p1,
        "P1_detail": {"lift": v},
        "P2_medqa_test_within_5_points_of_chance": p2,
        "P2_detail": {"lift": t, "tolerance": P2_TOL},
        "P3_negative_stems_lower_lift_in_all_three": p3,
        "P3_detail": p3_detail,
        "P4_medmcqa_negative_stems_below_chance": p4,
        "P4_detail": {"n": mneg.get("n"), "lift": mneg.get("lift")},
        "P5_mmlu_pro_negative_lift_below_half_positive": p5,
        "P5_detail": {"neg_lift": neg.get("lift"), "pos_lift": pos.get("lift"), "share": P5_SHARE},
        "P6_medmcqa_validation_lift_at_least_medqa_test": p6,
        "P6_detail": {"medmcqa_validation": v, "medqa_test": t},
        "P7_medmcqa_80pct_of_large_subjects_beat_chance": p7,
        "P7_detail": {"subjects": {s: r["lift"] for s, r in sorted(subj.items())}, "beat_chance": wins,
                      "min_n": P7_MIN_N, "share": P7_SHARE},
        "P8_medmcqa_contrast_survives_without_meta_options": p8,
        "P8_detail": c8,
    }
