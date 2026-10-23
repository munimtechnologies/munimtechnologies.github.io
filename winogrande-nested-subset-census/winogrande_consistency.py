"""Nested-subset and gold-consistency census for WinoGrande 1.1.

Part of MV2's eval-reliability-audits catalogue (Munim, Inc.). This research is carried out by
AI agents working in MV2's name.

WinoGrande (Sakaguchi et al., AAAI 2020) ships its training set in five nested sizes --
``train_xs`` ⊂ ``train_s`` ⊂ ``train_m`` ⊂ ``train_l`` ⊂ ``train_xl`` -- plus a ``dev`` split.
AllenAI's dataset card states "these training sets are nested subsets of each other (e.g. all the
instances in xs are in s)", and at least one published paper builds a validation split out of the
instances unique to ``train_xl`` *on the assumption that the nesting is exact*. But nobody has
verified id-by-id on the raw released files that (a) each smaller size is really a subset of the
next larger, (b) a question kept across sizes keeps the same gold answer, (c) no split contains two
questions with an identical ``(sentence, option1, option2)`` but a different gold, and (d) the dev
split shares no question id with the training set.

This census checks all four, treating a question's identity as its normalized
``(sentence, option1, option2)`` triple and its gold as the ``answer`` field ("1" or "2").

Apache-2.0.
"""


def normalize(s):
    """Collapse all whitespace runs to a single space, strip, and lowercase."""
    if s is None:
        return ""
    return " ".join(str(s).split()).lower()


def parse_row(obj):
    """Parse one WinoGrande jsonl object into a flat record.

    Fields: qID, sentence, option1, option2, answer. Identity is the normalized
    (sentence, option1, option2) triple; gold is str(answer).
    """
    qid = obj.get("qID")
    sentence = obj.get("sentence", "")
    opt1 = obj.get("option1", "")
    opt2 = obj.get("option2", "")
    answer = obj.get("answer")
    identity = (normalize(sentence), normalize(opt1), normalize(opt2))
    return {
        "qID": qid,
        "identity": identity,
        "answer": None if answer is None else str(answer).strip(),
        "qid_missing": qid is None,
    }


def within_file(records):
    """Census one split for duplicate ids and self-conflicting duplicate questions."""
    qid_counts = {}
    qid_answers = {}
    identity_answers = {}
    rows = 0
    qid_missing = 0
    for r in records:
        rows += 1
        if r["qid_missing"]:
            qid_missing += 1
        else:
            qid_counts[r["qID"]] = qid_counts.get(r["qID"], 0) + 1
            qid_answers.setdefault(r["qID"], set()).add(r["answer"])
        identity_answers.setdefault(r["identity"], []).append(r["answer"])
    identity_multi = sum(1 for a in identity_answers.values() if len(a) >= 2)
    identity_conflict = sum(1 for a in identity_answers.values() if len(set(a)) >= 2)
    # A qID that appears twice in ONE file with two different answers is its own data bug.
    qid_internal_conflict = sum(1 for a in qid_answers.values() if len(a) >= 2)
    return {
        "rows": rows,
        "qid_missing": qid_missing,
        "unique_qids": len(qid_counts),
        "duplicate_qids": sum(1 for n in qid_counts.values() if n > 1),
        "qid_internal_answer_conflict": qid_internal_conflict,
        "unique_identity_keys": len(identity_answers),
        "identity_keys_multi": identity_multi,
        "identity_keys_conflict": identity_conflict,
    }


def _qid_answer_map(records):
    """Map qID -> set of answers seen for it in a split."""
    m = {}
    for r in records:
        if not r["qid_missing"]:
            m.setdefault(r["qID"], set()).add(r["answer"])
    return m


def nesting(smaller_records, larger_records):
    """Check that `smaller` is a nested subset of `larger` by qID, with matching answers."""
    small = _qid_answer_map(smaller_records)
    large = _qid_answer_map(larger_records)
    only_in_smaller = 0
    shared = 0
    shared_answer_conflict = 0
    for qid, s_ans in small.items():
        if qid not in large:
            only_in_smaller += 1
            continue
        shared += 1
        # Both sides should carry one answer each; conflict if their answer sets differ.
        if s_ans != large[qid]:
            shared_answer_conflict += 1
    return {
        "smaller_unique_qids": len(small),
        "larger_unique_qids": len(large),
        "shared_qids": shared,
        "qids_only_in_smaller": only_in_smaller,
        "shared_answer_conflict": shared_answer_conflict,
    }


def overlap(a_records, b_records):
    """Count qIDs (and identities) shared by two splits (for a dev-vs-train leakage check)."""
    a_qids = {r["qID"] for r in a_records if not r["qid_missing"]}
    b_qids = {r["qID"] for r in b_records if not r["qid_missing"]}
    a_ids = {r["identity"] for r in a_records}
    b_ids = {r["identity"] for r in b_records}
    return {
        "shared_qids": len(a_qids & b_qids),
        "shared_identities": len(a_ids & b_ids),
    }


def census(ordered_splits):
    """Full census over an ordered list of (name, records).

    Computes within_file for each split and a nesting check for each adjacent pair
    (ordered_splits[i] is expected to be a subset of ordered_splits[i+1]).
    """
    ordered_splits = [(name, list(recs)) for name, recs in ordered_splits]
    within = {name: within_file(recs) for name, recs in ordered_splits}
    nest = {}
    for i in range(len(ordered_splits) - 1):
        a_name, a_recs = ordered_splits[i]
        b_name, b_recs = ordered_splits[i + 1]
        nest["%s->%s" % (a_name, b_name)] = nesting(a_recs, b_recs)
    return {"within": within, "nesting": nest}


def flatten(result, names, pairs):
    """Flatten a census to the flat keys used in the hand-traced TARGET.

    `names` are the split names to emit within-file stats for; `pairs` are
    (smaller, larger) nesting keys ("A->B").
    """
    flat = {}
    for name in names:
        w = result["within"][name]
        flat["%s_rows" % name] = w["rows"]
        flat["%s_unique_qids" % name] = w["unique_qids"]
        flat["%s_duplicate_qids" % name] = w["duplicate_qids"]
        flat["%s_unique_identity_keys" % name] = w["unique_identity_keys"]
        flat["%s_identity_keys_multi" % name] = w["identity_keys_multi"]
        flat["%s_identity_keys_conflict" % name] = w["identity_keys_conflict"]
    for key in pairs:
        n = result["nesting"][key]
        tag = key.replace("->", "_")
        flat["nest_%s_shared_qids" % tag] = n["shared_qids"]
        flat["nest_%s_qids_only_in_smaller" % tag] = n["qids_only_in_smaller"]
        flat["nest_%s_shared_answer_conflict" % tag] = n["shared_answer_conflict"]
    return flat


def public_summary(result, nesting_keys):
    """One-line human summary of nesting health across the given adjacent pairs."""
    viol = sum(result["nesting"][k]["qids_only_in_smaller"] for k in nesting_keys)
    conf = sum(result["nesting"][k]["shared_answer_conflict"] for k in nesting_keys)
    idc = sum(w["identity_keys_conflict"] for w in result["within"].values())
    return ("nesting violations (ids in a smaller set missing from the next larger): %d; "
            "cross-size answer conflicts: %d; within-split gold conflicts: %d." % (viol, conf, idc))
