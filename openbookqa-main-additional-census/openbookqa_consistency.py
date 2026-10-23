"""Main-vs-Additional gold-consistency census for OpenBookQA.

Part of MV2's eval-reliability-audits catalogue (Munim, Inc.). This research is carried out by
AI agents working in MV2's name.

OpenBookQA (Mihaylov et al., EMNLP 2018) ships every question twice: once in
``Data/Main/{split}.jsonl`` and once in ``Data/Additional/{split}_complete.jsonl``, where the
Additional copy adds the gold supporting fact and two human-rating fields. The dataset card and
the HuggingFace loader treat the two files as carrying the same questions and the same answer
keys, but that equivalence has never been verified id-by-id on the raw released files.

This census verifies it, and checks the files for internal gold conflicts, treating a question's
identity as (stem, set-of-choice-texts) and its gold as the TEXT of the chosen option:

- **Cross-file:** for every id shared by Main and Additional in the same split, do the two files
  agree on the answer key? Is any id present in only one of the two files?
- **Within-file:** does either file contain two questions with an identical (stem, choice-set)
  but a different gold answer (a self-conflicting duplicate)?

The gold is resolved from the answer key by finding the choice whose ``label`` equals
``answerKey``; a row whose key matches no choice label is counted as malformed and excluded from
the gold comparisons (its existence is still reported).

Apache-2.0.
"""


def normalize(s):
    """Collapse all whitespace runs to a single space, strip, and lowercase."""
    if s is None:
        return ""
    return " ".join(str(s).split()).lower()


def parse_row(obj, split):
    """Parse one OpenBookQA jsonl object into a flat record.

    Returns a dict with id, split, answer_key, identity key, and the normalized answer text
    (or None when the answer key matches no choice label -> malformed).
    """
    qid = obj.get("id")
    q = obj.get("question", {}) or {}
    stem = q.get("stem", "")
    choices = q.get("choices", []) or []
    key = obj.get("answerKey")
    answer_text = None
    for c in choices:
        if c.get("label") == key:
            answer_text = c.get("text")
            break
    ident = (normalize(stem), tuple(sorted(normalize(c.get("text", "")) for c in choices)))
    return {
        "id": qid,
        "split": split,
        "answer_key": key,
        "identity": ident,
        "answer_text": None if answer_text is None else normalize(answer_text),
        "malformed": answer_text is None,
    }


def within_file(records):
    """Census one file's parsed records for duplicate ids and self-conflicting duplicates."""
    id_counts = {}
    identity_golds = {}
    rows = 0
    malformed = 0
    for r in records:
        rows += 1
        id_counts[r["id"]] = id_counts.get(r["id"], 0) + 1
        if r["malformed"]:
            malformed += 1
            continue
        identity_golds.setdefault(r["identity"], []).append(r["answer_text"])
    multi = sum(1 for golds in identity_golds.values() if len(golds) >= 2)
    conflict = sum(1 for golds in identity_golds.values() if len(set(golds)) >= 2)
    return {
        "rows": rows,
        "malformed": malformed,
        "unique_ids": len(id_counts),
        "duplicate_ids": sum(1 for n in id_counts.values() if n > 1),
        "unique_identity_keys": len(identity_golds),
        "identity_keys_multi": multi,
        "identity_keys_conflict": conflict,
    }


def cross_file(main_records, additional_records):
    """Compare Main and Additional on every (split, id) they share."""
    main_map = {(r["split"], r["id"]): r for r in main_records}
    add_map = {(r["split"], r["id"]): r for r in additional_records}
    shared = main_map.keys() & add_map.keys()
    agree = 0
    disagree = 0
    text_disagree = 0
    examples = []
    for k in shared:
        m, a = main_map[k], add_map[k]
        if m["answer_key"] == a["answer_key"]:
            agree += 1
        else:
            disagree += 1
        if m["answer_text"] != a["answer_text"]:
            text_disagree += 1
        if (m["answer_key"] != a["answer_key"] or m["answer_text"] != a["answer_text"]) \
                and len(examples) < 50:
            examples.append({
                "split": k[0], "id": k[1],
                "main_key": m["answer_key"], "additional_key": a["answer_key"],
                "main_text": m["answer_text"], "additional_text": a["answer_text"],
            })
    return {
        "shared_ids": len(shared),
        "answerkey_agree": agree,
        "answerkey_disagree": disagree,
        "answer_text_disagree": text_disagree,
        "ids_only_in_main": len(main_map.keys() - add_map.keys()),
        "ids_only_in_additional": len(add_map.keys() - main_map.keys()),
        "examples": examples,
    }


def census(main_records, additional_records):
    """Full Main-vs-Additional census. Inputs are lists of parse_row dicts."""
    main_records = list(main_records)
    additional_records = list(additional_records)
    return {
        "main": within_file(main_records),
        "additional": within_file(additional_records),
        "crossfile": cross_file(main_records, additional_records),
    }


def flatten(result):
    """Flatten a census result to the flat keys used in the hand-traced TARGET."""
    m, a, x = result["main"], result["additional"], result["crossfile"]
    return {
        "main_rows": m["rows"],
        "main_malformed": m["malformed"],
        "main_unique_ids": m["unique_ids"],
        "main_duplicate_ids": m["duplicate_ids"],
        "main_unique_identity_keys": m["unique_identity_keys"],
        "main_identity_keys_multi": m["identity_keys_multi"],
        "main_identity_keys_conflict": m["identity_keys_conflict"],
        "additional_rows": a["rows"],
        "additional_malformed": a["malformed"],
        "additional_unique_ids": a["unique_ids"],
        "additional_duplicate_ids": a["duplicate_ids"],
        "additional_unique_identity_keys": a["unique_identity_keys"],
        "additional_identity_keys_multi": a["identity_keys_multi"],
        "additional_identity_keys_conflict": a["identity_keys_conflict"],
        "crossfile_shared_ids": x["shared_ids"],
        "crossfile_answerkey_agree": x["answerkey_agree"],
        "crossfile_answerkey_disagree": x["answerkey_disagree"],
        "crossfile_answer_text_disagree": x["answer_text_disagree"],
        "crossfile_ids_only_in_main": x["ids_only_in_main"],
        "crossfile_ids_only_in_additional": x["ids_only_in_additional"],
    }


def public_summary(result):
    """One-line human summary of a census result dict."""
    x = result["crossfile"]
    return (
        "Main %d rows / Additional %d rows; %d ids shared, %d answer-key disagreements, "
        "%d only in Main, %d only in Additional; within-file gold conflicts: Main %d, "
        "Additional %d." % (
            result["main"]["rows"], result["additional"]["rows"], x["shared_ids"],
            x["answerkey_disagree"], x["ids_only_in_main"], x["ids_only_in_additional"],
            result["main"]["identity_keys_conflict"],
            result["additional"]["identity_keys_conflict"],
        )
    )
