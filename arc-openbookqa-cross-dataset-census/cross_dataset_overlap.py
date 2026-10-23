"""Cross-dataset question-overlap census for two AI2 multiple-choice science QA benchmarks.

Part of MV2's eval-reliability-audits catalogue (Munim, Inc.). This research is carried out by
AI agents working in MV2's name.

ARC (Clark et al., 2018) and OpenBookQA (Mihaylov et al., 2018) are both AI2 grade-school science
multiple-choice benchmarks, and models are routinely trained and evaluated on them together. If any
question appears in both — the same stem with the same answer choices — then a split of one dataset
can silently leak into the training data of a model also fed the other, and if such a shared question
carries a different gold answer in the two datasets that is an outright cross-dataset labelling
conflict. Neither overlap has been measured on the raw released files.

This census treats a question's identity as its normalized ``(stem, set-of-choice-texts)`` and its
gold as the **text** of the choice whose ``label`` equals ``answerKey``. Both datasets share the same
raw jsonl question shape, so one parser serves both. A row whose ``answerKey`` matches no choice label
is counted as malformed and excluded from the identity/gold analysis.

Apache-2.0.
"""


def normalize(s):
    """Collapse all whitespace runs to a single space, strip, and lowercase."""
    if s is None:
        return ""
    return " ".join(str(s).split()).lower()


def parse_row(obj):
    """Parse one ARC/OpenBookQA jsonl object into a flat record.

    Both datasets use {"id", "question": {"stem", "choices": [{"text", "label"}, ...]}, "answerKey"}.
    A flat HuggingFace shape ({"question": "<stem>", "choices": {"text": [...], "label": [...]}}) is
    also accepted. Identity = (normalized stem, frozenset of normalized choice texts); gold =
    normalized text of the choice whose label == answerKey (None if no such choice -> malformed).
    """
    q = obj.get("question")
    if isinstance(q, dict):
        stem = q.get("stem", "")
        choices = q.get("choices", []) or []
        texts = [c.get("text", "") for c in choices]
        labels = [c.get("label", "") for c in choices]
    else:
        stem = q if isinstance(q, str) else ""
        ch = obj.get("choices", {}) or {}
        texts = list(ch.get("text", []) or [])
        labels = list(ch.get("label", []) or [])
    key = obj.get("answerKey")
    key = None if key is None else str(key).strip()
    label_to_text = {}
    for lab, txt in zip(labels, texts):
        label_to_text[str(lab).strip()] = txt
    malformed = key is None or key not in label_to_text
    gold = None if malformed else normalize(label_to_text.get(key))
    stem_n = normalize(stem)
    identity = (stem_n, frozenset(normalize(t) for t in texts))
    return {
        "id": obj.get("id"),
        "stem": stem_n,
        "identity": identity,
        "gold": gold,
        "malformed": malformed,
    }


def identity_gold_map(records):
    """Map identity -> set of golds seen (non-malformed rows only)."""
    m = {}
    for r in records:
        if not r["malformed"]:
            m.setdefault(r["identity"], set()).add(r["gold"])
    return m


def stem_set(records):
    """Set of normalized stems over non-malformed rows."""
    return {r["stem"] for r in records if not r["malformed"]}


def cross_overlap(a_records, b_records, max_examples=5):
    """Census two datasets for shared questions, shared-identity gold conflicts and shared stems.

    A shared identity is a normalized (stem, choice-set) present in both. A shared-identity gold
    conflict is a shared identity whose golds, pooled across both datasets, take two or more distinct
    values. A shared stem is a normalized stem present in both (a looser near-duplicate signal).
    """
    a_rows = len(a_records)
    b_rows = len(b_records)
    a_malformed = sum(1 for r in a_records if r["malformed"])
    b_malformed = sum(1 for r in b_records if r["malformed"])
    a_idg = identity_gold_map(a_records)
    b_idg = identity_gold_map(b_records)
    shared = sorted(set(a_idg) & set(b_idg), key=lambda idn: (idn[0], sorted(idn[1])))
    conflicts = [idn for idn in shared if len(a_idg[idn] | b_idg[idn]) >= 2]
    a_stems = stem_set(a_records)
    b_stems = stem_set(b_records)
    examples = []
    for idn in shared[:max_examples]:
        examples.append({
            "stem": idn[0],
            "choices": sorted(idn[1]),
            "a_golds": sorted(a_idg[idn]),
            "b_golds": sorted(b_idg[idn]),
            "gold_conflict": len(a_idg[idn] | b_idg[idn]) >= 2,
        })
    return {
        "a_rows": a_rows,
        "b_rows": b_rows,
        "a_malformed": a_malformed,
        "b_malformed": b_malformed,
        "a_distinct_identities": len(a_idg),
        "b_distinct_identities": len(b_idg),
        "a_distinct_stems": len(a_stems),
        "b_distinct_stems": len(b_stems),
        "shared_identities": len(shared),
        "shared_identity_gold_conflict": len(conflicts),
        "shared_stems": len(a_stems & b_stems),
        "examples": examples,
    }


def flatten(result):
    """Flatten the scalar census keys (drops examples) for comparison against a frozen TARGET."""
    return {k: v for k, v in result.items() if k != "examples"}
