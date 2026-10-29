"""META-OPTION classifier and census for multiple-choice questions (reused verbatim from audits 56/57).

A meta option is an answer choice that refers to the other choices instead of stating content on its own: "All of
the above", "None of these", "Both A and B", or the Roman-numeral sets of a statement-combination question ("I
only", "II and III", "I, II, and III"). Such options are conventionally placed last and cannot be permuted, so
they are a candidate construction-side mechanism for a benchmark's "the answer tends to be last" tilt.

Each question gets ONE category, by priority:
  roman      >= 2 options are Roman-numeral references AND at least one of them names >= 2 numerals
             (so a plain "I / II / III / IV" quadrant question is not counted)
  aota       some short option says "all/both of the above/these/those"
  nota       some short option says "none/neither of the above/these/those"
  letterref  some option is a combination of option letters ("Both A and B", "(a) and (c)", "A, B and C")
  plain      none of the above
"Short" means at most MAX_META_TOKENS whitespace tokens, so a long content answer that happens to contain the
phrase "all of the above-mentioned" is not counted.

For the per-category census, a question's meta options are the options matching its category's predicate.
Counts are exact; the chance baseline for "a meta option is the gold" is |meta options| / k per question, i.e.
what a uniformly placed gold would give. For roman questions the analogue is the unique most-inclusive option
(the one naming the most numerals), with chance 1/k.

Standard library + fractions only. Apache-2.0.
"""

import re
from fractions import Fraction

from position_census import question_validity

MAX_META_TOKENS = 10

AOTA_RE = re.compile(r"\b(?:all|both)\s+(?:of\s+)?(?:the\s+)?(?:above|these|those)\b", re.IGNORECASE)
NOTA_RE = re.compile(r"\b(?:none|neither)\s+(?:of\s+)?(?:the\s+)?(?:above|these|those)\b", re.IGNORECASE)

_SEP = r"(?:\s*,\s*and\s+|\s*,\s*|\s+and\s+|\s+or\s+|\s+nor\s+|\s*&\s*)"
_PREFIX = r"(?:(?:[Bb]oth|[Nn]either|[Oo]nly)\s+)?"
_NUM = r"(?:IV|V|I{1,3})"
_LET = r"(?:[A-D]|\([A-Da-d]\))"

# Whole-option matches (use .fullmatch on the stripped text). Case-sensitive numerals and letters on purpose.
ROMAN_RE = re.compile(_PREFIX + _NUM + r"(?:" + _SEP + _NUM + r")*(?:\s+only)?\.?")
LETTERREF_RE = re.compile(_PREFIX + _LET + r"(?:" + _SEP + _LET + r")+(?:\s+only)?"
                          r"(?:\s+(?:are|is)\s+(?:correct|true))?\.?")
ROMAN_TOKEN_RE = re.compile(r"\b" + _NUM + r"\b")

CATEGORIES = ("plain", "aota", "nota", "letterref", "roman")


def _text(t):
    return "" if t is None else str(t).strip()


def _short(t):
    return len(_text(t).split()) <= MAX_META_TOKENS


def is_aota(t):
    return _short(t) and AOTA_RE.search(_text(t)) is not None


def is_nota(t):
    return _short(t) and NOTA_RE.search(_text(t)) is not None


def is_letterref(t):
    return LETTERREF_RE.fullmatch(_text(t)) is not None


def is_roman(t):
    return ROMAN_RE.fullmatch(_text(t)) is not None


def roman_count(t):
    """Number of Roman-numeral tokens (I..V) in an option, e.g. 'I, II, and III' -> 3."""
    return len(ROMAN_TOKEN_RE.findall(_text(t)))


PREDICATES = {"aota": is_aota, "nota": is_nota, "letterref": is_letterref}


def classify_question(texts):
    """Return the single meta-option category of a question's option texts (see module docstring)."""
    roman_hits = [t for t in texts if is_roman(t)]
    if len(roman_hits) >= 2 and any(roman_count(t) >= 2 for t in roman_hits):
        return "roman"
    if any(is_aota(t) for t in texts):
        return "aota"
    if any(is_nota(t) for t in texts):
        return "nota"
    if any(is_letterref(t) for t in texts):
        return "letterref"
    return "plain"


def meta_indices(texts, category):
    """0-based indices of the options matching the category's predicate (empty for plain and roman)."""
    pred = PREDICATES.get(category)
    if pred is None:
        return []
    return [i for i, t in enumerate(texts) if pred(t)]


def most_inclusive_index(texts):
    """Index of the unique option naming the most Roman numerals, or None if the maximum is tied."""
    counts = [roman_count(t) for t in texts]
    top = max(counts)
    winners = [i for i, c in enumerate(counts) if c == top]
    return winners[0] if len(winners) == 1 else None


def _empty():
    return {
        "n": 0,
        "meta_pos_counts": {},       # first meta-option index -> count
        "n_meta_last": 0,            # the last option is a meta option
        "n_meta_gold": 0,            # the gold option is a meta option
        "n_multi_meta": 0,           # more than one option matches the category's predicate
        "expected_meta_gold": Fraction(0),       # sum over questions of |meta options| / k
        "n_inclusive_unique": 0,     # roman: a unique most-inclusive option exists
        "n_gold_inclusive": 0,       # roman: the gold is that unique most-inclusive option
        "expected_gold_inclusive": Fraction(0),  # roman: sum of 1/k over questions with a unique one
    }


def run_meta_census(rows):
    """rows: iterable of (key, labels, texts, answer_key); the key is ignored. Only valid questions count.

    Returns {category: {n, meta_pos_counts, n_meta_last, n_meta_gold, n_multi_meta, expected_meta_gold,
    n_inclusive_unique, n_gold_inclusive, expected_gold_inclusive}} for every category that occurs.
    """
    out = {}
    for _key, labels, texts, answer_key in rows:
        if question_validity(labels, texts, answer_key) != "valid":
            continue
        k = len(labels)
        gold = labels.index(answer_key)
        cat = classify_question(texts)
        b = out.setdefault(cat, _empty())
        b["n"] += 1
        idxs = meta_indices(texts, cat)
        if idxs:
            first = idxs[0]
            b["meta_pos_counts"][first] = b["meta_pos_counts"].get(first, 0) + 1
            if (k - 1) in idxs:
                b["n_meta_last"] += 1
            if gold in idxs:
                b["n_meta_gold"] += 1
            if len(idxs) > 1:
                b["n_multi_meta"] += 1
            b["expected_meta_gold"] += Fraction(len(idxs), k)
        if cat == "roman":
            inc = most_inclusive_index(texts)
            if inc is not None:
                b["n_inclusive_unique"] += 1
                b["expected_gold_inclusive"] += Fraction(1, k)
                if gold == inc:
                    b["n_gold_inclusive"] += 1
    return out


def meta_report(census):
    """JSON-serialisable view of run_meta_census output, with rates next to their chance baselines."""
    rep = {}
    for cat, b in census.items():
        n = b["n"]
        n_meta_q = sum(b["meta_pos_counts"].values())
        rep[cat] = {
            "n": n,
            "n_with_meta_option": n_meta_q,
            "meta_first_pos_counts": {str(p): b["meta_pos_counts"][p] for p in sorted(b["meta_pos_counts"])},
            "n_meta_last": b["n_meta_last"],
            "meta_last_rate": (b["n_meta_last"] / n_meta_q) if n_meta_q else None,
            "n_meta_gold": b["n_meta_gold"],
            "meta_gold_rate": (b["n_meta_gold"] / n_meta_q) if n_meta_q else None,
            "meta_gold_chance_rate": (float(b["expected_meta_gold"]) / n_meta_q) if n_meta_q else None,
            "n_multi_meta": b["n_multi_meta"],
            "n_inclusive_unique": b["n_inclusive_unique"],
            "n_gold_inclusive": b["n_gold_inclusive"],
            "gold_inclusive_rate": (b["n_gold_inclusive"] / b["n_inclusive_unique"]) if b["n_inclusive_unique"] else None,
            "gold_inclusive_chance_rate": ((float(b["expected_gold_inclusive"]) / b["n_inclusive_unique"])
                                           if b["n_inclusive_unique"] else None),
        }
    return rep
