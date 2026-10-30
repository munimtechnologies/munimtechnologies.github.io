"""Core of the MCQ gold-answer-length census.

For each multiple-choice question it measures how the length of the *gold* option compares with the
distractors, under two length definitions (characters after stripping, and whitespace tokens). The
aggregation is exact: tie-aware "pick the longest/shortest" credit and the random-choice baseline are carried
as `fractions.Fraction`, so the hand-traced fixture can be checked for exact equality before any real data is
read. Measures a construction-side property of the benchmark, not model behaviour.

The exact census core (question_validity, _per_question, run_census, to_report) is reused VERBATIM from audit 51
(mcq-gold-answer-length-census) via audits 52, 60, 61 and 62, so their hand-traced fixtures still check it for
exact equality. The core is key-agnostic and already handles a VARIABLE number of options per question (the chance
baseline is accumulated as sum(1/k)). Audit 63 keys it by SOURCE FAMILY and by (category, provenance) and adds no
logic here.

Standard library + fractions only. Apache-2.0.
"""

from fractions import Fraction


def clean(s):
    return (s or "").strip()


def char_len(s):
    return len(clean(s))


def token_len(s):
    return len(clean(s).split())


# Name -> length function. Both are reported; predictions use "char".
LENGTH_FUNCS = (("char", char_len), ("token", token_len))


def question_validity(labels, texts, answer_key):
    """Classify a raw question as 'valid', 'bad_key' (gold label absent) or 'degenerate' (unusable options)."""
    if labels is None or texts is None:
        return "degenerate"
    if len(labels) != len(texts):
        return "degenerate"
    if len(set(labels)) != len(labels):
        return "degenerate"
    if answer_key not in labels:
        return "bad_key"
    if len(labels) < 2:
        return "degenerate"
    return "valid"


def _per_question(labels, texts, answer_key, length_fn):
    """One question's length record under a single length function (assumes it is already 'valid')."""
    lens = [length_fn(t) for t in texts]
    gi = labels.index(answer_key)
    gold = lens[gi]
    others = [lens[i] for i in range(len(lens)) if i != gi]
    max_all = max(lens)
    min_all = min(lens)
    n_at_max = sum(1 for x in lens if x == max_all)
    n_at_min = sum(1 for x in lens if x == min_all)
    return {
        "gold": gold,
        "sum_distractor": sum(others),
        "n_distractor": len(others),
        "unique_longest": 1 if gold > max(others) else 0,
        "unique_shortest": 1 if gold < min(others) else 0,
        # tie-aware credit: a "pick the longest" rule that splits ties uniformly scores 1/n_at_max when the
        # gold sits at the maximum, else 0 -- the expected accuracy of that heuristic on this question.
        "longest_credit": Fraction(1, n_at_max) if gold == max_all else Fraction(0),
        "shortest_credit": Fraction(1, n_at_min) if gold == min_all else Fraction(0),
    }


def _new_accum():
    return {
        "n_valid": 0,
        "unique_longest": 0,
        "unique_shortest": 0,
        "sum_gold": 0,
        "sum_distractor": 0,
        "n_distractor": 0,
        "longest_credit": Fraction(0),
        "shortest_credit": Fraction(0),
    }


def run_census(rows):
    """rows: iterable of (key, labels, texts, answer_key). Returns per-key accumulators."""
    out = {}
    for bench, labels, texts, answer_key in rows:
        b = out.setdefault(bench, {
            "n_valid": 0,
            "n_bad_key": 0,
            "n_degenerate": 0,
            "option_count_hist": {},
            "chance_sum": Fraction(0),
            "char": _new_accum(),
            "token": _new_accum(),
        })
        v = question_validity(labels, texts, answer_key)
        if v == "bad_key":
            b["n_bad_key"] += 1
            continue
        if v == "degenerate":
            b["n_degenerate"] += 1
            continue
        b["n_valid"] += 1
        n_opt = len(labels)
        b["option_count_hist"][n_opt] = b["option_count_hist"].get(n_opt, 0) + 1
        b["chance_sum"] += Fraction(1, n_opt)
        for name, fn in LENGTH_FUNCS:
            r = _per_question(labels, texts, answer_key, fn)
            acc = b[name]
            acc["n_valid"] += 1
            acc["unique_longest"] += r["unique_longest"]
            acc["unique_shortest"] += r["unique_shortest"]
            acc["sum_gold"] += r["gold"]
            acc["sum_distractor"] += r["sum_distractor"]
            acc["n_distractor"] += r["n_distractor"]
            acc["longest_credit"] += r["longest_credit"]
            acc["shortest_credit"] += r["shortest_credit"]
    return out


def to_report(census):
    """Convert exact accumulators to a JSON-serialisable report of floats and counts."""
    rep = {}
    for bench, b in census.items():
        n = b["n_valid"]
        hist = b["option_count_hist"]
        modal_k = max(hist, key=lambda k: hist[k]) if hist else None
        entry = {
            "n_valid": n,
            "n_bad_key": b["n_bad_key"],
            "n_degenerate": b["n_degenerate"],
            "option_count_hist": {str(k): v for k, v in sorted(hist.items())},
            "modal_option_count": modal_k,
            "modal_coverage": (hist[modal_k] / n) if (n and modal_k is not None) else None,
            "chance_accuracy": float(b["chance_sum"] / n) if n else None,
        }
        for name in ("char", "token"):
            acc = b[name]
            nd = acc["n_distractor"]
            entry[name] = {
                "unique_longest_count": acc["unique_longest"],
                "unique_shortest_count": acc["unique_shortest"],
                "unique_longest_rate": acc["unique_longest"] / n if n else None,
                "unique_shortest_rate": acc["unique_shortest"] / n if n else None,
                "longest_accuracy": float(acc["longest_credit"] / n) if n else None,
                "shortest_accuracy": float(acc["shortest_credit"] / n) if n else None,
                "mean_gold_len": acc["sum_gold"] / n if n else None,
                "mean_distractor_len": acc["sum_distractor"] / nd if nd else None,
            }
        rep[bench] = entry
    return rep
