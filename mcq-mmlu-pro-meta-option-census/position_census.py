"""Core of the MCQ gold-answer-POSITION census (reused verbatim from audits 53/54/55/56).

For each multiple-choice question it records the 0-based INDEX of the gold option within the released option
list -- a construction-side property of the benchmark (where the author/converter placed the correct answer),
distinct from a model's position / selection bias (which is about how a model behaves when options are
permuted). Counts are exact integers; derived rates, a Pearson chi-square goodness-of-fit statistic against a
uniform gold-position distribution, and a best-constant-position baseline accuracy are computed in to_report.
The hand-traced fixture is checked for exact equality before any real data is read.

The gold position is bucketed by option count (k). "Position index" and "always pick position p" are only
well-defined within a fixed k, and each key is summarised at its modal option count.

The ONLY change from audit 56 is that CHI2_CRIT_0001 is extended to df = 12: MMLU-Pro has up to 10 options
(df = 9), beyond the df = 7 that four-option benchmarks needed. The added critical values are standard
chi-square table entries and do not affect any audit-56 result (which only used df <= 4).

Standard library + fractions only. Apache-2.0.
"""

from fractions import Fraction

# Upper-tail critical values of the chi-square distribution at alpha = 0.001, keyed by degrees of freedom
# (df = k - 1). From standard chi-square tables; used only to label a result "rejected at 0.001", and the raw
# statistic + df are always reported so a reader can compute an exact p-value themselves.
CHI2_CRIT_0001 = {
    1: 10.828, 2: 13.816, 3: 16.266, 4: 18.467, 5: 20.515, 6: 22.458, 7: 24.322,
    8: 26.124, 9: 27.877, 10: 29.588, 11: 31.264, 12: 32.909,
}
ALPHA = 0.001


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


def run_census(rows):
    """rows: iterable of (key, labels, texts, answer_key).

    Returns, per key, exact counts with gold-position counts bucketed by option count k:
      {key: {n_valid, n_bad_key, n_degenerate, by_option_count: {k: {n, pos_counts: {pos: count}}}}}.
    Labels are unique (checked in question_validity), so labels.index(answer_key) is the single gold position.
    """
    out = {}
    for key, labels, texts, answer_key in rows:
        b = out.setdefault(key, {
            "n_valid": 0,
            "n_bad_key": 0,
            "n_degenerate": 0,
            "by_option_count": {},  # k -> {"n": int, "pos_counts": {pos: count}}
        })
        v = question_validity(labels, texts, answer_key)
        if v == "bad_key":
            b["n_bad_key"] += 1
            continue
        if v == "degenerate":
            b["n_degenerate"] += 1
            continue
        b["n_valid"] += 1
        k = len(labels)
        pos = labels.index(answer_key)
        grp = b["by_option_count"].setdefault(k, {"n": 0, "pos_counts": {}})
        grp["n"] += 1
        grp["pos_counts"][pos] = grp["pos_counts"].get(pos, 0) + 1
    return out


def chi_square_uniform(pos_counts, k, n):
    """Pearson chi-square GOF statistic of the observed gold-position counts against a uniform(k) expectation."""
    exp = n / k
    stat = 0.0
    for p in range(k):
        obs = pos_counts.get(p, 0)
        stat += (obs - exp) ** 2 / exp
    return stat


def to_report(census):
    """Convert exact counts to a JSON-serialisable report. Each key is summarised at its modal k."""
    rep = {}
    for key, b in census.items():
        groups = b["by_option_count"]
        modal_k = max(groups, key=lambda k: groups[k]["n"]) if groups else None
        entry = {
            "n_valid": b["n_valid"],
            "n_bad_key": b["n_bad_key"],
            "n_degenerate": b["n_degenerate"],
            "option_count_hist": {str(k): groups[k]["n"] for k in sorted(groups)},
            "modal_option_count": modal_k,
            "modal_coverage": (groups[modal_k]["n"] / b["n_valid"]) if (modal_k is not None and b["n_valid"]) else None,
        }
        if modal_k is not None:
            g = groups[modal_k]
            n = g["n"]
            k = modal_k
            pc = g["pos_counts"]
            counts = [pc.get(p, 0) for p in range(k)]
            best_pos = max(range(k), key=lambda p: counts[p])
            best_count = counts[best_pos]
            stat = chi_square_uniform(pc, k, n)
            df = k - 1
            crit = CHI2_CRIT_0001.get(df)
            entry["modal"] = {
                "n": n,
                "pos_counts": {str(p): counts[p] for p in range(k)},
                "pos_rates": {str(p): (counts[p] / n) for p in range(k)},
                "chance_accuracy": 1.0 / k,
                "chi_square_stat": stat,
                "df": df,
                "chi_square_critical_0.001": crit,
                "uniform_rejected_0.001": (stat > crit) if crit is not None else None,
                "best_position": best_pos,
                "best_position_count": best_count,
                "best_position_accuracy": best_count / n,
                "best_position_accuracy_exact": str(Fraction(best_count, n)),
                "best_minus_chance": best_count / n - 1.0 / k,
            }
        rep[key] = entry
    return rep
