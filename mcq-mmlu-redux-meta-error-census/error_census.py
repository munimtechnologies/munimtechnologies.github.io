"""META-OPTION x ANNOTATION-ERROR census for MMLU-Redux (audit 58).

MMLU-Redux (Gema et al. 2024, "Are We Done with MMLU?", arXiv 2406.04127; CC BY 4.0) re-annotated 100 questions
from each of MMLU's 57 subjects and labelled each with an error_type: "ok", one of five error types, or "expert"
(annotators unsure; needs more expertise). Audit 56 showed that MMLU's "all of the above"-type META options sit
last, cue the gold, and explain most of its last-option tilt. This module asks a different question of the same
questions: are meta-option questions flagged as erroneous more often than plain ones?

Each valid question gets ONE meta-option category (meta_option.classify_question) and its normalised error label
is tallied per (subject, category). Error rates are taken over JUDGED questions only (ok + the five error types);
"expert" (unsure) and any undocumented label are counted but excluded from rates. Because meta options cluster in
a few subjects and error rates vary strongly by subject, the meta-vs-plain comparison is reported both pooled
(Pearson 2x2) and stratified by subject (Cochran-Mantel-Haenszel, no continuity correction, with the Mantel-
Haenszel common odds ratio).

Standard library only. Apache-2.0.
"""

import meta_option as mo
from position_census import question_validity

OK = "ok"
UNSURE = "expert"
ERROR_TYPES = ("bad_question_clarity", "bad_options_clarity", "no_correct_answer", "multiple_correct_answers",
               "wrong_groundtruth")
ANSWER_SET_ERRORS = ("no_correct_answer", "multiple_correct_answers")
DOCUMENTED_LABELS = (OK, UNSURE) + ERROR_TYPES
META_CATS = ("aota", "nota", "letterref", "roman")

# Upper-tail chi-square critical values for df = 1 (standard tables).
CHI2_CRIT_1DF_005 = 3.841
CHI2_CRIT_1DF_0001 = 10.828


def normalise_label(error_type):
    return "" if error_type is None else str(error_type).strip().lower()


def error_class(label):
    """'ok', 'error', 'unsure' or 'unknown' for a normalised error label."""
    if label == OK:
        return "ok"
    if label in ERROR_TYPES:
        return "error"
    if label == UNSURE:
        return "unsure"
    return "unknown"


def shape_mmlu(choices, answer):
    """MMLU-style row -> (labels, texts, answer_key): labels "0".."k-1", key = str(answer index)."""
    if choices is None:
        return None, None, None
    texts = ["" if t is None else str(t) for t in choices]
    labels = [str(i) for i in range(len(texts))]
    key = None if answer is None else str(int(answer))
    return labels, texts, key


def run_error_census(rows):
    """rows: iterable of (subject, labels, texts, answer_key, error_type).

    Returns {"n_rows", "n_invalid", "by_subject": {subject: {category: {normalised_label: count}}}}. Invalid
    questions are counted in n_invalid only.
    """
    out = {"n_rows": 0, "n_invalid": 0, "by_subject": {}}
    for subject, labels, texts, answer_key, error_type in rows:
        out["n_rows"] += 1
        if question_validity(labels, texts, answer_key) != "valid":
            out["n_invalid"] += 1
            continue
        cat = mo.classify_question(texts)
        lab = normalise_label(error_type)
        c = out["by_subject"].setdefault(subject, {}).setdefault(cat, {})
        c[lab] = c.get(lab, 0) + 1
    return out


def merge_counts(census, categories, subjects=None):
    """Sum the label counts over the given categories (and optionally only the given subjects)."""
    tot = {}
    for subj, bycat in census["by_subject"].items():
        if subjects is not None and subj not in subjects:
            continue
        for cat, counts in bycat.items():
            if cat in categories:
                for lab, n in counts.items():
                    tot[lab] = tot.get(lab, 0) + n
    return tot


def summarise_counts(counts):
    n = sum(counts.values())
    n_ok = counts.get(OK, 0)
    n_error = sum(counts.get(t, 0) for t in ERROR_TYPES)
    n_unsure = counts.get(UNSURE, 0)
    n_judged = n_ok + n_error
    n_as = sum(counts.get(t, 0) for t in ANSWER_SET_ERRORS)
    return {
        "n": n,
        "n_ok": n_ok,
        "n_error": n_error,
        "n_unsure": n_unsure,
        "n_unknown": n - n_ok - n_error - n_unsure,
        "n_judged": n_judged,
        "error_rate": (n_error / n_judged) if n_judged else None,
        "n_answer_set_error": n_as,
        "answer_set_error_rate": (n_as / n_judged) if n_judged else None,
        "error_type_rates": {t: (counts.get(t, 0) / n_judged) if n_judged else None for t in ERROR_TYPES},
        "label_counts": {lab: counts[lab] for lab in sorted(counts)},
    }


def pos_neg(counts, outcome):
    """(positives, negatives) among judged questions; outcome 'error' or 'answer_set'."""
    s = summarise_counts(counts)
    pos = s["n_error"] if outcome == "error" else s["n_answer_set_error"]
    return pos, s["n_judged"] - pos


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
    """Cochran-Mantel-Haenszel test over 2x2 strata (a, b, c, d), no continuity correction, df 1.

    Strata with fewer than 2 questions are skipped. Returns the statistic (None if no stratum is informative),
    the summed observed-minus-expected count in cell a (its sign is the direction of association) and the
    Mantel-Haenszel common odds ratio (None if its denominator is 0; numerator and denominator are reported).
    """
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


def stratified(census, cats1, cats2, outcome):
    """One (a, b, c, d) stratum per subject: group 1 = cats1, group 2 = cats2, positives per outcome."""
    strata = []
    for subj in sorted(census["by_subject"]):
        a, b = pos_neg(merge_counts(census, cats1, {subj}), outcome)
        c, d = pos_neg(merge_counts(census, cats2, {subj}), outcome)
        strata.append((a, b, c, d))
    return strata


def error_report(census):
    """JSON-serialisable report: per category, per group, pooled and subject-stratified comparisons."""
    subjects = census["by_subject"]
    cats_present = sorted({cat for bycat in subjects.values() for cat in bycat})
    groups = {"plain": ("plain",), "any_meta": META_CATS, "all": ("plain",) + META_CATS}
    rep = {
        "n_rows": census["n_rows"],
        "n_invalid": census["n_invalid"],
        "n_subjects": len(subjects),
        "by_category": {cat: summarise_counts(merge_counts(census, (cat,))) for cat in cats_present},
        "by_group": {g: summarise_counts(merge_counts(census, cats)) for g, cats in groups.items()},
    }
    all_labels = merge_counts(census, ("plain",) + META_CATS)
    rep["undocumented_labels"] = sorted(lab for lab in all_labels if lab not in DOCUMENTED_LABELS)
    pm = rep["by_group"]["any_meta"]
    pp = rep["by_group"]["plain"]
    pa = rep["by_category"].get("aota", summarise_counts({}))
    rep["meta_vs_plain_error_pooled"] = two_by_two(pm["n_error"], pm["n_judged"] - pm["n_error"],
                                                   pp["n_error"], pp["n_judged"] - pp["n_error"])
    rep["meta_vs_plain_error_by_subject_cmh"] = cmh(stratified(census, META_CATS, ("plain",), "error"))
    rep["aota_vs_plain_answer_set_pooled"] = two_by_two(
        pa["n_answer_set_error"], pa["n_judged"] - pa["n_answer_set_error"],
        pp["n_answer_set_error"], pp["n_judged"] - pp["n_answer_set_error"])
    rep["meta_vs_plain_answer_set_by_subject_cmh"] = cmh(stratified(census, META_CATS, ("plain",), "answer_set"))
    by_subj = {}
    for subj in sorted(subjects):
        sm = summarise_counts(merge_counts(census, META_CATS, {subj}))
        sp = summarise_counts(merge_counts(census, ("plain",), {subj}))
        by_subj[subj] = {"n_meta": sm["n"], "n_plain": sp["n"], "meta_error_rate": sm["error_rate"],
                         "plain_error_rate": sp["error_rate"], "meta_judged": sm["n_judged"],
                         "plain_judged": sp["n_judged"]}
    rep["by_subject"] = by_subj
    return rep
