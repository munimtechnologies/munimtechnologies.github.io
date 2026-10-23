"""Cross-set disjointness, cross-split leakage and gold-conflict census for the AI2 ARC dataset.

Part of MV2's eval-reliability-audits catalogue (Munim, Inc.). This research is carried out by
AI agents working in MV2's name.

ARC (Clark et al., 2018) partitions 7,787 grade-school science questions into a Challenge Set
(2,590 questions both a retrieval and a co-occurrence solver got wrong) and an Easy Set (the
remaining 5,197), each released with its own train/dev/test split. That construction makes three
structural promises a user relies on: that Easy and Challenge share no question, that a question
does not leak across the train/dev/test boundary within a set, and that no split carries the same
question twice with a different gold answer. None of these is verified on the raw released files.

This census checks all three, treating a question's identity as its normalized
``(stem, set-of-choice-texts)`` and its gold as the **text** of the choice whose ``label`` equals
``answerKey``. A row whose ``answerKey`` matches no choice label is counted as malformed and
excluded from the gold comparisons.

Apache-2.0.
"""


def normalize(s):
    """Collapse all whitespace runs to a single space, strip, and lowercase."""
    if s is None:
        return ""
    return " ".join(str(s).split()).lower()


def parse_row(obj):
    """Parse one ARC jsonl object (raw nested shape or flat HF shape) into a flat record.

    Raw ARC: {"id", "question": {"stem", "choices": [{"text", "label"}, ...]}, "answerKey"}.
    Flat HF: {"id", "question": "<stem>", "choices": {"text": [...], "label": [...]}, "answerKey"}.
    Identity = (normalized stem, frozenset of normalized choice texts); gold = normalized text of
    the choice whose label == answerKey (None if no such choice -> malformed).
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
    identity = (normalize(stem), frozenset(normalize(t) for t in texts))
    return {
        "id": obj.get("id"),
        "identity": identity,
        "gold": gold,
        "malformed": malformed,
        "id_missing": obj.get("id") is None,
    }


def within_file(records):
    """Census one split for duplicate ids, malformed rows and self-conflicting duplicate questions.

    Malformed rows (answerKey matches no choice) are counted but excluded from the identity/gold
    analysis, so they can never manufacture or hide a gold conflict.
    """
    id_counts = {}
    identity_golds = {}
    rows = 0
    id_missing = 0
    malformed = 0
    for r in records:
        rows += 1
        if r["id_missing"]:
            id_missing += 1
        else:
            id_counts[r["id"]] = id_counts.get(r["id"], 0) + 1
        if r["malformed"]:
            malformed += 1
            continue
        identity_golds.setdefault(r["identity"], []).append(r["gold"])
    identity_multi = sum(1 for g in identity_golds.values() if len(g) >= 2)
    identity_conflict = sum(1 for g in identity_golds.values() if len(set(g)) >= 2)
    return {
        "rows": rows,
        "id_missing": id_missing,
        "malformed": malformed,
        "unique_ids": len(id_counts),
        "duplicate_ids": sum(1 for n in id_counts.values() if n > 1),
        "unique_identity_keys": len(identity_golds),
        "identity_keys_multi": identity_multi,
        "identity_keys_conflict": identity_conflict,
    }


def _identity_gold_map(records):
    """Map identity -> set of golds seen (non-malformed rows only)."""
    m = {}
    for r in records:
        if not r["malformed"]:
            m.setdefault(r["identity"], set()).add(r["gold"])
    return m


def overlap(a_records, b_records):
    """Count ids and identities shared by two record lists, and shared-identity gold conflicts.

    shared_identity_gold_conflict counts shared identities whose golds, pooled across both sides,
    take two or more distinct values -- the same question appearing in both with a different gold.
    """
    a_ids = {r["id"] for r in a_records if not r["id_missing"]}
    b_ids = {r["id"] for r in b_records if not r["id_missing"]}
    a_idg = _identity_gold_map(a_records)
    b_idg = _identity_gold_map(b_records)
    shared_identities = set(a_idg) & set(b_idg)
    conflict = sum(1 for idn in shared_identities if len(a_idg[idn] | b_idg[idn]) >= 2)
    return {
        "shared_ids": len(a_ids & b_ids),
        "shared_identities": len(shared_identities),
        "shared_identity_gold_conflict": conflict,
    }


def flatten(within_map, overlap_map, names, pairs):
    """Flatten within-file and overlap stats to the flat keys used in the hand-traced TARGET."""
    flat = {}
    for name in names:
        w = within_map[name]
        flat["%s_rows" % name] = w["rows"]
        flat["%s_malformed" % name] = w["malformed"]
        flat["%s_unique_ids" % name] = w["unique_ids"]
        flat["%s_duplicate_ids" % name] = w["duplicate_ids"]
        flat["%s_unique_identity_keys" % name] = w["unique_identity_keys"]
        flat["%s_identity_keys_multi" % name] = w["identity_keys_multi"]
        flat["%s_identity_keys_conflict" % name] = w["identity_keys_conflict"]
    for a, b in pairs:
        o = overlap_map[(a, b)]
        tag = "%s_%s" % (a, b)
        flat["ov_%s_shared_ids" % tag] = o["shared_ids"]
        flat["ov_%s_shared_identities" % tag] = o["shared_identities"]
        flat["ov_%s_shared_identity_gold_conflict" % tag] = o["shared_identity_gold_conflict"]
    return flat
