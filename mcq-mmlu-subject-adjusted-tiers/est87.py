"""Audit 87: tiers adjusted by subject. New functions only; audit 85's are in base87.py.

Audit 85 found that wrong-key rates by model-vote tier, pooled over MMLU's subjects, rank questions well but place
wrong keys across subjects worse than Redux's own subject rates. This module combines the two by indirect
standardisation with a shrinkage prior: for each subject s, k_s = (O_s + A) / (E_s + A), where O_s is the subject's
observed wrong keys among the training questions, E_s the sum of their tier rates, and A the prior weight. A
question's probability is min(1, tier rate x k_s). A stratified bootstrap (resampling judged training questions
within each subject, then drawing each target question's outcome) gives a 95% predictive interval for a total.
Standard library only. Apache-2.0. Authored by AI agents working in the name of MV2, Munim, Inc.
"""

import random
from fractions import Fraction

import base87 as qm


def subject_factors(tiers, subject_of, target, judged, train, rate, pooled, prior):
    """{subject: k_s} over the judged questions in train: k_s = (O_s + prior) / (E_s + prior), O_s = questions of s
    in target, E_s = sum of their tier rates (the pooled rate for a tier without a rate)."""
    obs, exp = {}, {}
    for q in judged:
        if q not in train:
            continue
        s = subject_of[q]
        obs[s] = obs.get(s, 0) + (1 if q in target else 0)
        exp[s] = exp.get(s, Fraction(0)) + rate.get(tiers[q], pooled)
    return {s: (obs[s] + prior) / (exp[s] + prior) for s in obs}


def adjusted_predict(tiers, subject_of, rate, pooled, factors, qs):
    """{q: min(1, tier rate x subject factor)}; a subject without a factor uses 1."""
    out = {}
    for q in qs:
        p = rate.get(tiers[q], pooled) * factors.get(subject_of[q], Fraction(1))
        out[q] = min(p, Fraction(1))
    return out


def fit_adjusted(tiers, subject_of, target, judged, train, prior):
    """(tier rate, pooled rate, subject factors) fitted on the judged questions in train."""
    rate, pooled, _den = qm.rates(tiers, target, judged, train)
    return rate, pooled, subject_factors(tiers, subject_of, target, judged, train, rate, pooled, prior)


def cross_fold_adjusted(tiers, subject_of, fold, target, judged, prior):
    """For each fold f: fit on the judged questions of the other fold, predict the judged questions of fold f.
    Returns [{fold, n_test, actual, adj_expected, mae_adj}]."""
    out = []
    for f in (0, 1):
        train = {q for q in judged if fold[q] != f}
        test = [q for q in sorted(judged) if fold[q] == f]
        rate, pooled, fac = fit_adjusted(tiers, subject_of, target, judged, train, prior)
        p = adjusted_predict(tiers, subject_of, rate, pooled, fac, test)
        out.append({"fold": f, "n_test": len(test), "actual": sum(1 for q in test if q in target),
                    "adj_expected": sum(p.values(), Fraction(0)),
                    "mae_adj": qm.subject_abs_error(p, target, subject_of)})
    return out


def pct_bounds(b):
    """Indices of the 2.5th and 97.5th percentiles in a sorted list of b values: floor(0.025 b) and
    ceil(0.975 b) - 1, in integer arithmetic."""
    return (b * 25) // 1000, -(-(b * 975) // 1000) - 1


def _sample_fit(tiers, subject_of, target, sample, prior):
    """Float tier rates, pooled rate and subject factors from a list of questions that may repeat."""
    num, den = {}, {}
    for q in sample:
        t = tiers[q]
        den[t] = den.get(t, 0) + 1
        if q in target:
            num[t] = num.get(t, 0) + 1
    pooled = (sum(num.values()) / len(sample)) if sample else 0.0
    rate = {t: num.get(t, 0) / den[t] for t in den}
    obs, exp = {}, {}
    for q in sample:
        s = subject_of[q]
        obs[s] = obs.get(s, 0) + (1 if q in target else 0)
        exp[s] = exp.get(s, 0.0) + rate.get(tiers[q], pooled)
    fac = {s: (obs[s] + prior) / (exp[s] + prior) for s in obs}
    return rate, pooled, fac


def bootstrap_total(tiers, subject_of, target, train, qs, prior, b, seed):
    """Stratified bootstrap predictive interval for the number of target questions among qs. Each replicate
    resamples the training questions with replacement within each subject (same count per subject), refits the
    adjusted model and draws each question of qs as a hit with its probability. Returns (low, high, totals sorted)."""
    rng = random.Random(seed)
    by_s = {}
    for q in sorted(train):
        by_s.setdefault(subject_of[q], []).append(q)
    subjects = sorted(by_s)
    qs = sorted(qs)
    totals = []
    for _ in range(b):
        sample = []
        for s in subjects:
            lst = by_s[s]
            n = len(lst)
            sample.extend(lst[rng.randrange(n)] for _ in range(n))
        rate, pooled, fac = _sample_fit(tiers, subject_of, target, sample, float(prior))
        tot = 0
        for q in qs:
            p = min(1.0, rate.get(tiers[q], pooled) * fac.get(subject_of[q], 1.0))
            if rng.random() < p:
                tot += 1
        totals.append(tot)
    totals.sort()
    lo, hi = pct_bounds(b)
    return totals[lo], totals[hi], totals


def predictions87(adj_folds, base_folds, adj_err_folds, base_err_folds, boot, est_adj, est_tier, est_subject):
    """Pre-registered P2-P5 (P1 is decided in job.py).
    adj_folds / base_folds: cross_fold_adjusted (prior 1) and base87.cross_fold outputs for wrong keys;
    adj_err_folds / base_err_folds: the same for any error label; boot: [(low, high)] per fold, built on the other
    fold; est_*: estimates of wrong keys among the unreviewed questions."""
    ma = sum((f["mae_adj"] for f in adj_folds), Fraction(0))
    ms = sum((f["mae_subject"] for f in base_folds), Fraction(0))
    mt = sum((f["mae_tier"] for f in base_folds), Fraction(0))
    ea = sum((f["mae_adj"] for f in adj_err_folds), Fraction(0))
    es = sum((f["mae_subject"] for f in base_err_folds), Fraction(0))
    lo, hi = sorted([est_subject, est_tier])
    return {
        "P2_adjusted_beats_subject": ma < ms,
        "P2_mae": [float(ma), float(ms), float(mt)],
        "P3_interval_covers": all(lo_ <= f["actual"] <= hi_ for f, (lo_, hi_) in zip(adj_folds, boot)),
        "P3_folds": [[f["actual"], float(f["adj_expected"]), lo_, hi_] for f, (lo_, hi_) in zip(adj_folds, boot)],
        "P4_between": lo < est_adj < hi,
        "P4_estimates": [float(est_adj), float(est_subject), float(est_tier)],
        "P5_errors_adjusted_beats_subject": ea < es,
        "P5_mae": [float(ea), float(es)],
    }
