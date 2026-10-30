"""Join MMLU-Pro's MMLU-derived questions back to MMLU and split each question's distractors by origin (audit 62).

MMLU-Pro expanded MMLU's 4-option questions to (mostly) 10 options. For a question inherited from MMLU
(`src` starting "ori_mmlu"), this module finds the same question in MMLU by whitespace-normalised question text,
checks that the gold answer text is unchanged, and labels every MMLU-Pro distractor as ORIGINAL (its normalised
text equals one of MMLU's three distractors) or ADDED (anything else, i.e. introduced by the expansion). It then
accumulates, exactly, how the gold option's length compares with each kind of distractor:

- mean length of the gold, the original distractors and the added distractors (characters after stripping);
- a pairwise "gold is longer" rate per distractor kind (1 if gold longer, 1/2 if equal, 0 if shorter);
- on INTACT questions (all three MMLU distractors retained), the tie-aware pick-longest credit on the full
  MMLU-Pro option list and on the 4-option original subset (gold + the three original distractors).

Measures a construction property of the benchmark, not model behaviour. Standard library + fractions only.
Apache-2.0.
"""

from fractions import Fraction

from gold_length import char_len


STATUSES = ("matched", "no_question", "no_gold", "ambiguous", "bad_key")


def norm(s):
    """Whitespace-normalised text used for joining (case and punctuation are kept)."""
    return " ".join((s or "").split())


def provenance(src):
    return "ori_mmlu" if (src or "").startswith("ori_mmlu") else "other"


def build_index(mmlu_rows):
    """mmlu_rows: iterable of (subject, question, choices, answer_index). Returns norm(question) -> candidates.

    Each candidate is (subject, norm(gold text), sorted tuple of norm(distractor texts)). Rows whose answer index
    is not a valid position are skipped.
    """
    index = {}
    for subject, question, choices, ans in mmlu_rows:
        choices = list(choices or [])
        if not isinstance(ans, int) or ans < 0 or ans >= len(choices):
            continue
        gold = norm(choices[ans])
        distractors = tuple(sorted(norm(c) for i, c in enumerate(choices) if i != ans))
        index.setdefault(norm(question), []).append((subject, gold, distractors))
    return index


def match_question(question, options, answer_index, index):
    """Classify one MMLU-Pro question against the MMLU index.

    Returns (status, split). status is one of STATUSES. For 'matched', split is (gold_text, original_texts,
    added_texts) holding the RAW MMLU-Pro option texts; otherwise split is None. A question is 'ambiguous' when
    MMLU holds the same question text with the same gold text but different distractor sets.
    """
    options = list(options or [])
    if not isinstance(answer_index, int) or answer_index < 0 or answer_index >= len(options):
        return "bad_key", None
    cands = index.get(norm(question))
    if not cands:
        return "no_question", None
    gold = norm(options[answer_index])
    sets = set(d for (_subject, g, d) in cands if g == gold)
    if not sets:
        return "no_gold", None
    if len(sets) > 1:
        return "ambiguous", None
    original_set = set(next(iter(sets)))
    original = []
    added = []
    for i, opt in enumerate(options):
        if i == answer_index:
            continue
        if norm(opt) in original_set:
            original.append(opt)
        else:
            added.append(opt)
    return "matched", (options[answer_index], original, added)


def _pair_score(g, d):
    if g > d:
        return Fraction(1)
    if g == d:
        return Fraction(1, 2)
    return Fraction(0)


def longest_credit(gold_len, other_lens):
    """Tie-aware pick-longest credit: 1/(number of options at the maximum) if the gold is at the maximum, else 0."""
    m = max([gold_len] + list(other_lens))
    if gold_len < m:
        return Fraction(0)
    return Fraction(1, 1 + sum(1 for x in other_lens if x == m))


def new_accum():
    return {
        "n_questions": 0,
        "retained_hist": {},
        "n_with_added": 0,
        "sum_gold": 0,
        "n_original": 0,
        "sum_original": 0,
        "gold_vs_original": Fraction(0),
        "n_added": 0,
        "sum_added": 0,
        "gold_vs_added": Fraction(0),
        "n_intact": 0,
        "intact_full_longest": Fraction(0),
        "intact_full_chance": Fraction(0),
        "intact_orig_longest": Fraction(0),
    }


def add_question(acc, gold, original, added, length_fn=char_len):
    g = length_fn(gold)
    o = [length_fn(t) for t in original]
    a = [length_fn(t) for t in added]
    acc["n_questions"] += 1
    acc["retained_hist"][len(o)] = acc["retained_hist"].get(len(o), 0) + 1
    if a:
        acc["n_with_added"] += 1
    acc["sum_gold"] += g
    acc["n_original"] += len(o)
    acc["sum_original"] += sum(o)
    acc["n_added"] += len(a)
    acc["sum_added"] += sum(a)
    for x in o:
        acc["gold_vs_original"] += _pair_score(g, x)
    for x in a:
        acc["gold_vs_added"] += _pair_score(g, x)
    if len(o) == 3:
        acc["n_intact"] += 1
        acc["intact_full_longest"] += longest_credit(g, o + a)
        acc["intact_full_chance"] += Fraction(1, 1 + len(o) + len(a))
        acc["intact_orig_longest"] += longest_credit(g, o)


def run_join(pro_rows, index, length_fn=char_len):
    """pro_rows: iterable of (category, src, question, options, answer_index).

    Only ori_mmlu rows are joined. Returns (status_counts, accums) where accums is keyed by "ALL" and by category.
    """
    status_counts = {s: 0 for s in STATUSES}
    accs = {}
    for category, src, question, options, answer_index in pro_rows:
        if provenance(src) != "ori_mmlu":
            continue
        st, split = match_question(question, options, answer_index, index)
        status_counts[st] += 1
        if st != "matched":
            continue
        gold, original, added = split
        for key in ("ALL", category):
            add_question(accs.setdefault(key, new_accum()), gold, original, added, length_fn)
    return status_counts, accs


def _ratio(num, den):
    return float(num) / den if den else None


def summarize(acc):
    """JSON-serialisable floats and counts from one exact accumulator."""
    n_intact = acc["n_intact"]
    return {
        "n_questions": acc["n_questions"],
        "retained_hist": {str(k): v for k, v in sorted(acc["retained_hist"].items())},
        "n_with_added": acc["n_with_added"],
        "mean_gold_len": _ratio(acc["sum_gold"], acc["n_questions"]),
        "n_original_distractors": acc["n_original"],
        "mean_original_len": _ratio(acc["sum_original"], acc["n_original"]),
        "n_added_distractors": acc["n_added"],
        "mean_added_len": _ratio(acc["sum_added"], acc["n_added"]),
        "gold_longer_vs_original": _ratio(acc["gold_vs_original"], acc["n_original"]),
        "gold_longer_vs_added": _ratio(acc["gold_vs_added"], acc["n_added"]),
        "n_intact": n_intact,
        "intact_pick_longest_full": _ratio(acc["intact_full_longest"], n_intact),
        "intact_chance_full": _ratio(acc["intact_full_chance"], n_intact),
        "intact_pick_longest_original4": _ratio(acc["intact_orig_longest"], n_intact),
        "intact_chance_original4": 0.25 if n_intact else None,
    }
