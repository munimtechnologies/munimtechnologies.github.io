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
