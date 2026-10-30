"""Within-source checks of MMLU-Pro's answer-length pull over every published prediction archive (audit 66).

Audit 65 found that 15 models' wrong answers land on a longest distractor more often than a random wrong pick, most
on the STEM-website biology and psychology questions, and that models are far more accurate on STEM-website
questions when the gold is the unique longest option. Two things it left open:

- that accuracy gap was crude: the gold is the unique longest mostly in prose subjects, which models find easier.
  Here it is stratified by `src` (Mantel-Haenszel risk difference: within each src, accuracy with the gold unique
  longest minus accuracy otherwise, pooled with weights n1*n0/(n1+n0));
- the error pull only asks "longest or not". Here every wrong pick also gets a normalised length mid-rank among the
  distractors (0 shortest .. 1 longest, ties averaged; the mean over a question's distractors is exactly 0.5), the
  same scale Turkish MMLU Pro (arXiv 2609.15467) reports for its models.

Standard library only. Apache-2.0.
"""

from fractions import Fraction

import model_length as ml

MIN_RANK_N = 30   # P3 needs at least this many ranked wrong answers in both biology + psychology subsets
P2_LOW, P2_HIGH = 0.51, 0.56


def length_rank(options, gold, pick):
    """Normalised mid-rank (0 shortest .. 1 longest) of the picked distractor's length among all distractors.
    None when the pick is missing, out of range or the gold, or there are fewer than two distractors."""
    L = ml.lens(options)
    k = len(L)
    if pick is None or k < 3 or not 0 <= pick < k or pick == gold:
        return None
    dl = [L[j] for j in range(k) if j != gold]
    x = L[pick]
    less = sum(1 for v in dl if v < x)
    equal = sum(1 for v in dl if v == x)
    return Fraction(2 * less + equal - 1, 2 * (len(dl) - 1))


def new_strata_acc():
    return {"rank_n": 0, "rank_sum": Fraction(0), "src": {}}


def add_strata(acc, src, options, gold, pred):
    """Accumulate one (question, prediction): per-src gold-unique-longest cells and the wrong pick's length rank.
    Cell = [n gold unique-longest, correct, n gold not unique-longest, correct]."""
    L = ml.lens(options)
    k = len(L)
    m = max(L)
    gold_ul = L[gold] == m and L.count(m) == 1
    i = ml.pred_index(pred, k)
    correct = i is not None and i == gold
    cell = acc["src"].setdefault(src, [0, 0, 0, 0])
    if gold_ul:
        cell[0] += 1
        cell[1] += 1 if correct else 0
    else:
        cell[2] += 1
        cell[3] += 1 if correct else 0
    if i is not None and not correct:
        r = length_rank(options, gold, i)
        if r is not None:
            acc["rank_n"] += 1
            acc["rank_sum"] += r


def mh_risk_difference(cells):
    """Mantel-Haenszel risk difference over strata [n1, c1, n0, c0]; strata missing either group are skipped.
    Returns (Fraction or None, strata used, questions used)."""
    num = Fraction(0)
    den = Fraction(0)
    used = 0
    n_used = 0
    for n1, c1, n0, c0 in cells:
        if n1 == 0 or n0 == 0:
            continue
        big_n = n1 + n0
        num += Fraction(c1 * n0 - c0 * n1, big_n)
        den += Fraction(n1 * n0, big_n)
        used += 1
        n_used += big_n
    return (num / den if den else None), used, n_used


def report_strata(acc):
    cells = list(acc["src"].values())
    rd, used, n_used = mh_risk_difference(cells)
    n1 = sum(c[0] for c in cells)
    c1 = sum(c[1] for c in cells)
    n0 = sum(c[2] for c in cells)
    c0 = sum(c[3] for c in cells)
    crude = (Fraction(c1, n1) - Fraction(c0, n0)) if (n1 and n0) else None
    return {
        "length_rank_n": acc["rank_n"],
        "length_rank_mean": float(acc["rank_sum"] / acc["rank_n"]) if acc["rank_n"] else None,
        "mh_rd_gold_ul": float(rd) if rd is not None else None,
        "mh_strata": used,
        "mh_n": n_used,
        "crude_rd_gold_ul": float(crude) if crude is not None else None,
    }


def avg_ranks(xs):
    """1-based ranks with ties averaged."""
    order = sorted(range(len(xs)), key=lambda t: xs[t])
    r = [0.0] * len(xs)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and xs[order[j + 1]] == xs[order[i]]:
            j += 1
        avg = (i + j) / 2 + 1
        for t in range(i, j + 1):
            r[order[t]] = avg
        i = j + 1
    return r


def spearman(xs, ys):
    if len(xs) < 3 or len(xs) != len(ys):
        return None
    rx, ry = avg_ranks(xs), avg_ranks(ys)
    n = len(xs)
    mx, my = sum(rx) / n, sum(ry) / n
    sxy = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    sxx = sum((a - mx) ** 2 for a in rx)
    syy = sum((b - my) ** 2 for b in ry)
    if sxx == 0 or syy == 0:
        return None
    return sxy / (sxx * syy) ** 0.5


def _median(vals):
    v = sorted(vals)
    if not v:
        return None
    mid = len(v) // 2
    return v[mid] if len(v) % 2 else (v[mid - 1] + v[mid]) / 2


def _get(models, m, key, field):
    return models[m].get(key, {}).get(field)


def predictions(models, heuristic_biopsy, new_models):
    """Pre-registered predictions over the included models. models: name -> {key: merged report}.
    new_models: included models that were not in audit 65. Decided before any new archive was opened."""
    names = sorted(models)

    # P1: wrong picks sit above the middle of the distractor length order (mean rank > 0.5) in a strict majority.
    ranks = {m: _get(models, m, "ALL", "length_rank_mean") for m in names}
    p1_wins = [m for m in names if ranks[m] is not None and ranks[m] > 0.5]
    p1 = bool(names) and 2 * len(p1_wins) > len(names)

    # P2: the median model's pooled length rank lies in [0.51, 0.56] (Turkish MMLU Pro reports 0.515-0.536).
    med = _median([r for r in ranks.values() if r is not None])
    p2 = med is not None and P2_LOW <= med <= P2_HIGH

    # P3: length rank higher on STEM-website biology+psychology than on MMLU-derived biology+psychology, in a strict
    # majority of models with at least MIN_RANK_N ranked wrong answers in both.
    elig3, wins3 = [], []
    for m in names:
        sn, on = _get(models, m, "sub:stemez-biopsy", "length_rank_n"), _get(models, m, "sub:ori-biopsy",
                                                                             "length_rank_n")
        if not sn or not on or sn < MIN_RANK_N or on < MIN_RANK_N:
            continue
        elig3.append(m)
        if _get(models, m, "sub:stemez-biopsy", "length_rank_mean") > _get(models, m, "sub:ori-biopsy",
                                                                           "length_rank_mean"):
            wins3.append(m)
    p3 = bool(elig3) and 2 * len(wins3) > len(elig3)

    # P4: within-src (Mantel-Haenszel) accuracy advantage when the gold is the unique longest is positive on stemez
    # in a strict majority of models.
    s_rd = {m: _get(models, m, "fam:stemez", "mh_rd_gold_ul") for m in names}
    o_rd = {m: _get(models, m, "fam:ori_mmlu", "mh_rd_gold_ul") for m in names}
    elig4 = [m for m in names if s_rd[m] is not None]
    wins4 = [m for m in elig4 if s_rd[m] > 0]
    p4 = bool(elig4) and 2 * len(wins4) > len(elig4)

    # P5: that within-src advantage is larger on stemez than on ori_mmlu in a strict majority of models.
    elig5 = [m for m in names if s_rd[m] is not None and o_rd[m] is not None]
    wins5 = [m for m in elig5 if s_rd[m] > o_rd[m]]
    p5 = bool(elig5) and 2 * len(wins5) > len(elig5)

    # P6: across models, overall accuracy and pooled error pull are negatively rank-correlated.
    pairs = [(_get(models, m, "ALL", "accuracy"), _get(models, m, "ALL", "error_pull_ratio")) for m in names]
    pairs = [(a, b) for a, b in pairs if a is not None and b is not None]
    rho = spearman([a for a, _ in pairs], [b for _, b in pairs])
    p6 = rho is not None and rho < 0

    # P7: at least one model not in audit 65 scores below the pick-longest heuristic on STEM-website bio+psy.
    below_new = [m for m in sorted(new_models) if m in models
                 and _get(models, m, "sub:stemez-biopsy", "accuracy") is not None
                 and _get(models, m, "sub:stemez-biopsy", "accuracy") < heuristic_biopsy]
    below_all = [m for m in names if _get(models, m, "sub:stemez-biopsy", "accuracy") is not None
                 and _get(models, m, "sub:stemez-biopsy", "accuracy") < heuristic_biopsy]
    p7 = len(below_new) >= 1

    return {
        "P1_length_rank_above_half_in_majority": p1,
        "P1_detail": {"models_above": p1_wins, "length_rank_all": ranks},
        "P2_median_length_rank_in_0_51_0_56": p2,
        "P2_detail": {"median": med, "range": [P2_LOW, P2_HIGH]},
        "P3_stemez_biopsy_rank_above_ori_biopsy_in_majority": p3,
        "P3_detail": {"eligible": elig3, "wins": wins3, "min_rank_n": MIN_RANK_N},
        "P4_within_src_gold_longest_advantage_positive_on_stemez": p4,
        "P4_detail": {"eligible": len(elig4), "positive": wins4, "mh_rd_stemez": s_rd},
        "P5_within_src_advantage_larger_on_stemez_than_ori": p5,
        "P5_detail": {"eligible": len(elig5), "wins": wins5, "mh_rd_ori_mmlu": o_rd},
        "P6_accuracy_and_error_pull_negatively_correlated": p6,
        "P6_detail": {"spearman": rho, "n_models": len(pairs)},
        "P7_a_new_model_below_pick_longest_on_stemez_biopsy": p7,
        "P7_detail": {"heuristic": heuristic_biopsy, "new_models_below": below_new, "all_models_below": below_all},
    }
