"""Row conversion, data-quality counts, position test, structural gate and pre-registered predictions for the
SuperGPQA answer-length census (audit 64).

SuperGPQA gives each question an `options` list, an `answer_letter` (A, B, ...) and the `answer` text. The census
takes the gold position from the letter; the answer text is only used to count letter/text disagreements.

Standard library only. Apache-2.0.
"""

from fractions import Fraction

import gold_length as gl

MIN_DISCIPLINE_N = 100   # a discipline needs at least this many valid questions to enter P8
MIN_POSITION_N = 100     # P7 needs at least this many 10-option questions
CHI2_CRIT_DF9 = 27.877   # chi-square critical value, df 9, p = 0.001
EXAMPLES_MAX = 20


def letter_index(letter):
    """'A' -> 0, 'B' -> 1, ...; None for anything that is not a single upper-case letter."""
    s = (letter or "").strip()
    if len(s) == 1 and "A" <= s <= "Z":
        return ord(s) - ord("A")
    return None


def calc_key(v):
    if v is True:
        return "calculation"
    if v is False:
        return "text"
    return "unknown"


def census_rows(sg_rows, key_fn):
    """(key, labels, texts, answer_key) rows for gold_length.run_census, labelled by option position."""
    out = []
    for r in sg_rows:
        opts = list(r["options"] or [])
        idx = letter_index(r["answer_letter"])
        out.append((key_fn(r), [str(j) for j in range(len(opts))], opts, "?" if idx is None else str(idx)))
    return out


def mmlu_pro_rows(pro_rows, key_fn):
    """MMLU-Pro rows (options, answer_index) in the same form, as in audits 59-63."""
    out = []
    for r in pro_rows:
        opts = list(r["options"] or [])
        out.append((key_fn(r), [str(j) for j in range(len(opts))], opts, str(r["answer_index"])))
    return out


def digest(census):
    """Exact summary of raw census accumulators: key -> (n_valid, n_bad_key, chance_sum, char longest_credit)."""
    return {k: (b["n_valid"], b["n_bad_key"], b["chance_sum"], b["char"]["longest_credit"])
            for k, b in census.items()}


def quality(sg_rows):
    """Counts of letter/text disagreements and duplicated option texts (after strip). Returns (counts, examples)."""
    q = {"n_rows": 0, "letter_unparseable": 0, "letter_out_of_range": 0, "letter_text_mismatch": 0,
         "gold_duplicated": 0, "any_duplicate_options": 0}
    ex = {"letter_text_mismatch": [], "gold_duplicated": []}

    def note(name, r):
        q[name] += 1
        if name in ex and len(ex[name]) < EXAMPLES_MAX:
            ex[name].append(r["uuid"])

    for r in sg_rows:
        q["n_rows"] += 1
        opts = [gl.clean(o) for o in (r["options"] or [])]
        if len(set(opts)) < len(opts):
            q["any_duplicate_options"] += 1
        idx = letter_index(r["answer_letter"])
        if idx is None:
            q["letter_unparseable"] += 1
            note("letter_text_mismatch", r)
            continue
        if idx >= len(opts):
            q["letter_out_of_range"] += 1
            note("letter_text_mismatch", r)
            continue
        if opts[idx] != gl.clean(r["answer"]):
            note("letter_text_mismatch", r)
        if opts.count(opts[idx]) > 1:
            note("gold_duplicated", r)
    return q, ex


def position_chi2(indices, k):
    """Goodness of fit of gold positions 0..k-1 to uniform. Exact chi-square as a Fraction."""
    counts = [0] * k
    for i in indices:
        counts[i] += 1
    n = len(indices)
    if not n:
        return {"n": 0, "counts": counts, "chi2": Fraction(0)}
    e = Fraction(n, k)
    chi2 = sum(((c - e) ** 2 / e for c in counts), Fraction(0))
    return {"n": n, "counts": counts, "chi2": chi2}


def ten_option_positions(sg_rows):
    """Gold positions of the questions that have exactly 10 options and a letter inside them."""
    out = []
    for r in sg_rows:
        opts = r["options"] or []
        idx = letter_index(r["answer_letter"])
        if len(opts) == 10 and idx is not None and idx < 10:
            out.append(idx)
    return out


def _close(a, b):
    return a is not None and abs(a - b) < 1e-12


def structural_gate(pooled_pro, expected):
    """The pipeline must reproduce audit 61's pooled MMLU-Pro census exactly. Returns (ok, detail)."""
    detail = {
        "n_valid": {"got": pooled_pro["n_valid"], "expected": expected["n_valid"],
                    "match": pooled_pro["n_valid"] == expected["n_valid"]},
        "pooled_unique_longest": {"got": pooled_pro["char"]["unique_longest_count"],
                                  "expected": expected["unique_longest"],
                                  "match": pooled_pro["char"]["unique_longest_count"] == expected["unique_longest"]},
        "pooled_longest_accuracy": {"got": pooled_pro["char"]["longest_accuracy"],
                                    "expected": expected["longest_accuracy"],
                                    "match": _close(pooled_pro["char"]["longest_accuracy"],
                                                    expected["longest_accuracy"])},
        "clean_parse": {"got": [pooled_pro["n_bad_key"], pooled_pro["n_degenerate"]], "expected": [0, 0],
                        "match": pooled_pro["n_bad_key"] == 0 and pooled_pro["n_degenerate"] == 0},
    }
    return all(d["match"] for d in detail.values()), detail


def lift(e):
    return e["char"]["longest_accuracy"] - e["chance_accuracy"]


def ratio(e):
    return e["char"]["longest_accuracy"] / e["chance_accuracy"]


def _lift_or_none(e):
    return lift(e) if (e and e["n_valid"]) else None


def predictions(pooled, by_calc, by_diff, by_disc, qual, pos):
    """Pre-registered predictions, each a finding either way. Decided before any real number was seen.
    pos = {"n": ..., "chi2": float} for the 10-option questions."""
    c = pooled["char"]
    # P1: the "similar lengths" design holds up: pick-longest scores under 1.5x chance (MMLU-Pro: 1.66x, audit 61).
    p1 = ratio(pooled) < 1.5
    # P2: but a residual shortcut remains: pick-longest beats chance by at least 1 percentage point.
    p2 = lift(pooled) >= 0.01
    # P3: text (non-calculation) questions carry a larger lift than calculation questions.
    t, k = by_calc.get("text"), by_calc.get("calculation")
    p3 = bool(t and k and t["n_valid"] and k["n_valid"]) and lift(t) > lift(k)
    # P4: easy questions carry a larger lift than hard questions.
    ez, hd = by_diff.get("easy"), by_diff.get("hard")
    p4 = bool(ez and hd and ez["n_valid"] and hd["n_valid"]) and lift(ez) > lift(hd)
    # P5: the gold is longer than the average distractor in characters (as the paper's token means suggest).
    p5 = c["mean_distractor_len"] is not None and c["mean_gold_len"] > c["mean_distractor_len"]
    # P6: the gold is the unique longest option more often than the unique shortest.
    p6 = c["unique_longest_count"] > c["unique_shortest_count"]
    # P7: gold positions of the 10-option questions are uniform (chi-square df 9 below the p = 0.001 value).
    p7 = pos["n"] >= MIN_POSITION_N and pos["chi2"] < CHI2_CRIT_DF9
    # P8: pick-longest beats chance in a strict majority of disciplines with n >= 100.
    elig = sorted(k2 for k2, v in by_disc.items() if v["n_valid"] >= MIN_DISCIPLINE_N)
    pos_disc = [d for d in elig if lift(by_disc[d]) > 0]
    p8 = bool(elig) and 2 * len(pos_disc) > len(elig)
    # P9: the answer text equals the option named by answer_letter in every question.
    p9 = qual["letter_text_mismatch"] == 0

    return {
        "P1_pooled_pick_longest_under_1_5x_chance": p1,
        "P1_detail": {"ratio": ratio(pooled)},
        "P2_pooled_lift_at_least_1pp": p2,
        "P2_detail": {"lift": lift(pooled)},
        "P3_text_lift_exceeds_calculation_lift": p3,
        "P3_detail": {"text": _lift_or_none(t), "calculation": _lift_or_none(k)},
        "P4_easy_lift_exceeds_hard_lift": p4,
        "P4_detail": {"easy": _lift_or_none(ez), "hard": _lift_or_none(hd)},
        "P5_gold_longer_than_mean_distractor": p5,
        "P5_detail": {"gold": c["mean_gold_len"], "distractor": c["mean_distractor_len"]},
        "P6_unique_longest_exceeds_unique_shortest": p6,
        "P6_detail": {"unique_longest": c["unique_longest_count"], "unique_shortest": c["unique_shortest_count"]},
        "P7_ten_option_positions_uniform": p7,
        "P7_detail": {"n": pos["n"], "chi2": pos["chi2"], "critical_df9_p001": CHI2_CRIT_DF9},
        "P8_lift_positive_in_majority_of_disciplines": p8,
        "P8_detail": {"eligible": elig, "positive": pos_disc},
        "P9_answer_text_matches_letter_everywhere": p9,
        "P9_detail": {"letter_text_mismatch": qual["letter_text_mismatch"]},
    }
