"""Do real models' MMLU-Pro answers follow the answer-length cue? Core logic for audit 65.

Audits 61-63 measured a construction property: on MMLU-Pro a question-free "pick the longest option" heuristic
scores 18.38% pooled and about 67% on the STEM-website (src stemez-) biology and psychology questions. This module
reads the per-question model predictions TIGER-AI-Lab publishes for MMLU-Pro and asks whether the models' answers
lean the same way:

- error pull: when a model answers wrongly, how often its chosen option is a longest distractor, against the rate a
  uniformly random wrong choice would give (exact, tie-aware);
- accuracy when the gold is the unique longest option versus when it is not.

Standard library only. Apache-2.0.
"""

from fractions import Fraction

LETTERS = "ABCDEFGHIJ"
BIOPSY_STEMEZ = ("stemez-Biology", "stemez-Psychology")
BIOPSY_CATEGORIES = ("biology", "psychology")


def family(src):
    """Source family: the src prefix before the first '-' (e.g. 'stemez-Biology' -> 'stemez')."""
    s = src or ""
    return s.split("-", 1)[0] if s else "unknown"


def lens(options):
    return [len(str(o).strip()) for o in options]


def pred_index(pred, k):
    """Index of a predicted letter A-J within k options, or None when missing / malformed / out of range."""
    if not isinstance(pred, str):
        return None
    p = pred.strip().upper()
    if len(p) != 1 or p not in LETTERS:
        return None
    i = LETTERS.index(p)
    return i if i < k else None


def pick_longest_credit(options, gold):
    """Tie-aware expected credit of 'pick the longest option' on one question."""
    L = lens(options)
    m = max(L)
    return Fraction(1, L.count(m)) if L[gold] == m else Fraction(0)


def new_acc():
    return {"n": 0, "n_none": 0, "n_correct": 0, "n_wrong": 0,
            "obs_longest": 0, "base_longest": Fraction(0),
            "n_gold_ul": 0, "correct_gold_ul": 0, "n_gold_not_ul": 0, "correct_gold_not_ul": 0}


def add(acc, options, gold, pred):
    """Accumulate one (question, model prediction). A missing or malformed prediction counts as not correct."""
    L = lens(options)
    k = len(L)
    acc["n"] += 1
    m = max(L)
    gold_ul = L[gold] == m and L.count(m) == 1
    i = pred_index(pred, k)
    correct = i is not None and i == gold
    if gold_ul:
        acc["n_gold_ul"] += 1
        acc["correct_gold_ul"] += 1 if correct else 0
    else:
        acc["n_gold_not_ul"] += 1
        acc["correct_gold_not_ul"] += 1 if correct else 0
    if i is None:
        acc["n_none"] += 1
        return
    if correct:
        acc["n_correct"] += 1
        return
    acc["n_wrong"] += 1
    dl = [L[j] for j in range(k) if j != gold]
    dm = max(dl)
    acc["obs_longest"] += 1 if L[i] == dm else 0
    acc["base_longest"] += Fraction(dl.count(dm), len(dl))


def _norm_options(opts):
    return [str(o).strip() for o in (opts or [])]


def _qid(x):
    try:
        return int(x)
    except (TypeError, ValueError):
        return None


def join_status(rec, hf_by_id):
    """'ok' | 'no_id' | 'options_differ' | 'answer_differ' for one prediction record against the HF test row."""
    q = hf_by_id.get(_qid(rec.get("question_id")))
    if q is None:
        return "no_id"
    if _norm_options(rec.get("options")) != _norm_options(q["options"]):
        return "options_differ"
    if "answer_index" in rec and rec["answer_index"] is not None:
        if _qid(rec["answer_index"]) != q["answer_index"]:
            return "answer_differ"
    elif "answer" in rec and rec["answer"] is not None:
        a = str(rec["answer"]).strip().upper()
        if a != LETTERS[q["answer_index"]]:
            return "answer_differ"
    return "ok"


def keys_for(row):
    """Accumulator keys one HF row contributes to."""
    fam = family(row["src"])
    out = ["ALL", "fam:" + fam]
    if row["src"] in BIOPSY_STEMEZ:
        out.append("sub:stemez-biopsy")
    if fam == "ori_mmlu" and row["category"] in BIOPSY_CATEGORIES:
        out.append("sub:ori-biopsy")
    return out


def report(acc):
    """Floats for one accumulator (exact sums kept as strings alongside)."""
    n, nw = acc["n"], acc["n_wrong"]
    base = acc["base_longest"]
    return {
        "n": n,
        "n_none": acc["n_none"],
        "accuracy": acc["n_correct"] / n if n else None,
        "n_wrong": nw,
        "wrong_on_longest_distractor": acc["obs_longest"] / nw if nw else None,
        "wrong_on_longest_distractor_baseline": float(base / nw) if nw else None,
        "error_pull_ratio": (acc["obs_longest"] / float(base)) if base else None,
        "obs_longest": acc["obs_longest"],
        "base_longest_exact": "%d/%d" % (base.numerator, base.denominator),
        "n_gold_unique_longest": acc["n_gold_ul"],
        "accuracy_gold_unique_longest": acc["correct_gold_ul"] / acc["n_gold_ul"] if acc["n_gold_ul"] else None,
        "n_gold_not_unique_longest": acc["n_gold_not_ul"],
        "accuracy_gold_not_unique_longest": (acc["correct_gold_not_ul"] / acc["n_gold_not_ul"]
                                             if acc["n_gold_not_ul"] else None),
    }


def predictions(models, heuristic_biopsy, min_group=20):
    """Pre-registered predictions over the included models. models: name -> {key: report}. Decided before any data."""
    names = sorted(models)
    ratio_all = {m: models[m]["ALL"]["error_pull_ratio"] for m in names}

    # P1: in a strict majority of models, wrong answers land on a longest distractor more often than random.
    p1_wins = [m for m in names if ratio_all[m] is not None and ratio_all[m] > 1.0]
    p1 = bool(names) and 2 * len(p1_wins) > len(names)

    # P2: in a strict majority of models, the error pull is larger on stemez than on ori_mmlu questions.
    p2_wins = []
    for m in names:
        s = models[m].get("fam:stemez", {}).get("error_pull_ratio")
        o = models[m].get("fam:ori_mmlu", {}).get("error_pull_ratio")
        if s is not None and o is not None and s > o:
            p2_wins.append(m)
    p2 = bool(names) and 2 * len(p2_wins) > len(names)

    # P3: on stemez biology+psychology, every model is more accurate when the gold is the unique longest option.
    p3_detail = {}
    p3 = bool(names)
    for m in names:
        r = models[m].get("sub:stemez-biopsy")
        if (not r or r["n_gold_unique_longest"] < min_group or r["n_gold_not_unique_longest"] < min_group):
            p3 = False
            p3_detail[m] = None
            continue
        gap = r["accuracy_gold_unique_longest"] - r["accuracy_gold_not_unique_longest"]
        p3_detail[m] = gap
        if not gap > 0:
            p3 = False

    # P4: models below the median overall accuracy have a larger mean pooled error pull than the rest.
    accs = sorted(models[m]["ALL"]["accuracy"] for m in names)
    if accs:
        mid = len(accs) // 2
        median = accs[mid] if len(accs) % 2 else (accs[mid - 1] + accs[mid]) / 2
    else:
        median = None
    low = [ratio_all[m] for m in names if median is not None and ratio_all[m] is not None
           and models[m]["ALL"]["accuracy"] < median]
    high = [ratio_all[m] for m in names if median is not None and ratio_all[m] is not None
            and models[m]["ALL"]["accuracy"] >= median]
    mean_low = sum(low) / len(low) if low else None
    mean_high = sum(high) / len(high) if high else None
    p4 = mean_low is not None and mean_high is not None and mean_low > mean_high

    # P5: at least a quarter of models score below the pick-longest heuristic on stemez biology+psychology.
    below = [m for m in names
             if models[m].get("sub:stemez-biopsy", {}).get("accuracy") is not None
             and models[m]["sub:stemez-biopsy"]["accuracy"] < heuristic_biopsy]
    p5 = bool(names) and 4 * len(below) >= len(names)

    return {
        "P1_error_pull_above_random_in_majority_of_models": p1,
        "P1_detail": {"models_above_1": p1_wins, "ratio_all": ratio_all},
        "P2_error_pull_larger_on_stemez_in_majority_of_models": p2,
        "P2_detail": {"models_stemez_larger": p2_wins},
        "P3_stemez_biopsy_more_accurate_when_gold_longest_for_every_model": p3,
        "P3_detail": {"accuracy_gap_gold_ul_minus_not": p3_detail, "min_group": min_group},
        "P4_weaker_models_pulled_more": p4,
        "P4_detail": {"median_accuracy": median, "mean_ratio_below_median": mean_low,
                      "mean_ratio_at_or_above_median": mean_high},
        "P5_quarter_of_models_below_pick_longest_on_stemez_biopsy": p5,
        "P5_detail": {"heuristic": heuristic_biopsy, "models_below": below},
    }
