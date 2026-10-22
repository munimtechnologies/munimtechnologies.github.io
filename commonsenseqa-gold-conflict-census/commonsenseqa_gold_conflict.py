"""Census of duplicate questions with conflicting gold answers in CommonsenseQA.

Part of MV2's eval-reliability-audits catalogue (Munim, Inc.). This research is carried
out by AI agents working in MV2's name.

A CommonsenseQA example is a question stem with five labelled choices (A-E) and an
``answerKey`` naming the correct one. The identity of a question is its stem together with
its *set* of option texts; the gold is the TEXT of the chosen option (not the letter), so a
reshuffled-but-equivalent question is not counted as a defect. If the SAME (stem, option
set) appears more than once with a DIFFERENT gold answer text, the gold is self-contradicting
and any score computed against it is partly noise. The same stem paired with a DIFFERENT
option set is NOT a defect; it is reported separately, as context.

Apache-2.0.
"""
from collections import defaultdict


def normalize(s):
    """Collapse all whitespace runs to a single space, strip, and lowercase."""
    if s is None:
        return ""
    return " ".join(str(s).split()).lower()


def _choices(row):
    """Return the list of {'label','text'} choice dicts, or raise on a bad shape."""
    q = row.get("question")
    if not isinstance(q, dict):
        raise KeyError("row has no 'question' dict")
    ch = q.get("choices")
    if not isinstance(ch, list) or not ch:
        raise KeyError("row 'question' has no non-empty 'choices' list")
    return ch


def stem_of(row):
    """Return the question stem string, or raise."""
    q = row.get("question")
    if not isinstance(q, dict) or q.get("stem") is None:
        raise KeyError("row has no 'question.stem'")
    return q["stem"]


def choice_texts(row):
    """Return the list of option texts for a row (order as released)."""
    texts = []
    for c in _choices(row):
        if not isinstance(c, dict) or c.get("text") is None:
            raise KeyError("choice has no 'text': %r" % (c,))
        texts.append(c["text"])
    return texts


def gold_text(row):
    """Return the TEXT of the choice whose label == answerKey.

    Raises KeyError/ValueError if answerKey is missing or names no existing label, so a
    schema change can never be silently read as a single class.
    """
    key = row.get("answerKey")
    if key is None:
        raise KeyError("row has no 'answerKey'")
    key = str(key).strip()
    for c in _choices(row):
        if str(c.get("label")).strip() == key:
            if c.get("text") is None:
                raise ValueError("chosen choice has no text")
            return c["text"]
    raise ValueError("answerKey %r matches no choice label" % (key,))


def census(rows):
    """Count duplicate (stem, option-set) questions with conflicting gold answer texts.

    rows: iterable of CommonsenseQA dicts. Returns a dict of integer counts plus a small
    list of real conflict examples. The option-set key is the sorted tuple of option texts,
    so option order does not matter; the gold compared is the answer TEXT, so relabelling
    the same answer is not a conflict.
    """
    rows = list(rows)
    n = len(rows)

    exact_item = defaultdict(list)   # (stem, sorted option texts)             -> gold texts
    norm_item = defaultdict(list)    # (norm stem, sorted norm option texts)   -> norm golds
    stem_count = defaultdict(int)    # stem                                    -> example count
    unique_stems = set()
    malformed = 0

    for r in rows:
        try:
            stem = stem_of(r)
            texts = choice_texts(r)
            gold = gold_text(r)
        except (KeyError, ValueError):
            malformed += 1
            continue
        unique_stems.add(stem)
        stem_count[stem] += 1
        exact_key = (stem, tuple(sorted(texts)))
        norm_key = (normalize(stem), tuple(sorted(normalize(t) for t in texts)))
        exact_item[exact_key].append(gold)
        norm_item[norm_key].append(normalize(gold))

    item_dup_groups = 0
    item_conflict_groups = 0
    item_conflict_rows = 0
    exact_conflict_norm_keys = set()
    item_conflict_examples = []
    for (stem, opts), golds in exact_item.items():
        if len(golds) >= 2:
            item_dup_groups += 1
        if len(set(golds)) >= 2:
            item_conflict_groups += 1
            item_conflict_rows += len(golds)
            exact_conflict_norm_keys.add(
                (normalize(stem), tuple(sorted(normalize(o) for o in opts))))
            if len(item_conflict_examples) < 10:
                item_conflict_examples.append({
                    "stem": stem[:200],
                    "options": [o[:80] for o in opts],
                    "gold_texts": sorted(set(golds)),
                    "n_rows": len(golds),
                })

    norm_item_conflict_groups = 0
    norm_additional = 0
    for key, golds in norm_item.items():
        if len(set(golds)) >= 2:
            norm_item_conflict_groups += 1
            if key not in exact_conflict_norm_keys:
                norm_additional += 1

    stem_duplicate_groups = sum(1 for c in stem_count.values() if c >= 2)

    return {
        "rows": n,
        "malformed": malformed,
        "unique_stems": len(unique_stems),
        "unique_items": len(exact_item),
        "item_duplicate_groups": item_dup_groups,
        "item_conflict_groups": item_conflict_groups,
        "item_conflict_rows": item_conflict_rows,
        "norm_item_conflict_groups": norm_item_conflict_groups,
        "norm_additional": norm_additional,
        "stem_duplicate_groups": stem_duplicate_groups,
        "item_conflict_examples": item_conflict_examples,
    }


def public_summary(result):
    """One-line human summary of a census result dict."""
    return (
        "%d rows, %d unique stems, %d unique (stem, option-set) items; "
        "%d item duplicate groups, %d with conflicting gold answers (%d rows); "
        "%d normalized conflicts (%d additional); "
        "%d stems reused across examples (context)." % (
            result["rows"], result["unique_stems"], result["unique_items"],
            result["item_duplicate_groups"], result["item_conflict_groups"],
            result["item_conflict_rows"], result["norm_item_conflict_groups"],
            result["norm_additional"], result["stem_duplicate_groups"],
        )
    )
