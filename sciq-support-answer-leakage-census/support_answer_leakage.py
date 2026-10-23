"""Does SciQ's gold support passage lexically reveal the correct answer?

Part of MV2's eval-reliability-audits catalogue (Munim, Inc.). This research is carried out by
AI agents working in MV2's name.

SciQ (Welbl, Liu and Gardner, 2017) is a crowdsourced multiple-choice science benchmark. For most
questions it ships a ``support`` passage: a paragraph of evidence intended to help a reader find the
correct answer. That makes SciQ usable "open book" (answer from the support) or "closed book" (answer
from the question alone). This census measures, on the released files, exactly how answer-bearing that
support passage is: how often the normalized text of the **correct answer** occurs as a substring of
the normalized ``support``, versus how often a **distractor** does, and how many questions ship with no
support passage at all.

A large gold-over-distractor asymmetry means the support passage is a legitimate answer leak that a
closed-book evaluation of SciQ must account for; parity would mean the support does not give the answer
away by surface form. Substring containment is contiguous and case/whitespace-normalized only
(punctuation kept), so the reported leak counts are a conservative lower bound.

Apache-2.0.
"""

_DISTRACTOR_KEYS = ("distractor1", "distractor2", "distractor3")


def normalize(s):
    """Collapse all whitespace runs to a single space, strip, and lowercase."""
    if s is None:
        return ""
    return " ".join(str(s).split()).lower()


def parse_row(obj):
    """Parse one SciQ json object into a flat record.

    Shape: {"question", "correct_answer", "distractor1", "distractor2", "distractor3", "support"}.
    A row missing the ``correct_answer`` key is malformed and excluded. Returns the normalized gold
    answer text (None if malformed), the normalized distractor texts present, all normalized choice
    texts, and the normalized support.
    """
    has_gold = "correct_answer" in obj
    gold = normalize(obj.get("correct_answer")) if has_gold else None
    distractors = [normalize(obj.get(k)) for k in _DISTRACTOR_KEYS if k in obj]
    support = normalize(obj.get("support"))
    choice_texts = ([gold] if has_gold else []) + distractors
    return {
        "question": normalize(obj.get("question")),
        "gold_text": gold,
        "distractor_texts": distractors,
        "choice_texts": choice_texts,
        "support": support,
        "malformed": not has_gold,
    }


def support_answer_stats(records, max_examples=5):
    """Count lexical answer leakage of the gold support over a list of parsed records.

    A valid row with a non-empty support contributes to the leak rates. The gold answer is "in support"
    if its normalized text is non-empty and a substring of the normalized support; each distractor is
    tested the same way. Rows whose support is empty are counted separately and excluded from the rates
    (there is nothing to leak into). ``support == a choice`` is a verbatim whole-support match to a
    choice text. Rates compare the per-question gold hit rate to the per-distractor hit rate (so option
    count is controlled for).
    """
    n_valid = 0
    n_malformed = 0
    n_with_support = 0
    n_empty_support = 0
    n_gold_in_support = 0
    n_any_distractor_in_support = 0
    total_distractor_in_support = 0
    n_distractors_total = 0
    n_support_eq_a_choice = 0
    examples = []
    for r in records:
        if r["malformed"]:
            n_malformed += 1
            continue
        n_valid += 1
        support = r["support"]
        if not support:
            n_empty_support += 1
            continue
        n_with_support += 1
        gold = r["gold_text"]
        if gold and gold in support:
            n_gold_in_support += 1
            if len(examples) < max_examples:
                examples.append({
                    "question": r["question"][:120],
                    "gold": gold,
                    "support": support[:160],
                })
        d_hits = sum(1 for d in r["distractor_texts"] if d and d in support)
        total_distractor_in_support += d_hits
        n_distractors_total += len(r["distractor_texts"])
        if d_hits:
            n_any_distractor_in_support += 1
        if support in r["choice_texts"]:
            n_support_eq_a_choice += 1
    gold_rate = (n_gold_in_support / n_with_support) if n_with_support else 0.0
    distractor_rate = (total_distractor_in_support / n_distractors_total) if n_distractors_total else 0.0
    return {
        "n_valid": n_valid,
        "n_malformed": n_malformed,
        "n_with_support": n_with_support,
        "n_empty_support": n_empty_support,
        "n_gold_in_support": n_gold_in_support,
        "n_any_distractor_in_support": n_any_distractor_in_support,
        "total_distractor_in_support": total_distractor_in_support,
        "n_distractors_total": n_distractors_total,
        "n_support_eq_a_choice": n_support_eq_a_choice,
        "gold_coverage_rate": gold_rate,
        "distractor_coverage_rate": distractor_rate,
        "examples": examples,
    }


def flatten(stats):
    """Integer census keys only (drops rates and examples) for comparison against a frozen TARGET."""
    keep = (
        "n_valid", "n_malformed", "n_with_support", "n_empty_support", "n_gold_in_support",
        "n_any_distractor_in_support", "total_distractor_in_support", "n_distractors_total",
        "n_support_eq_a_choice",
    )
    return {k: stats[k] for k in keep}
