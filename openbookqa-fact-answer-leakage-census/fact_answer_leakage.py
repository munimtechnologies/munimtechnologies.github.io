"""Does OpenBookQA's annotated gold fact lexically reveal the correct answer?

Part of MV2's eval-reliability-audits catalogue (Munim, Inc.). This research is carried out by
AI agents working in MV2's name.

OpenBookQA (Mihaylov et al., 2018) ships an "Additional" release in which every multiple-choice
question is annotated with the single core science ``fact1`` it was written against. The benchmark's
stated premise is that this fact is *not* enough on its own: answering also needs a second, unstated
piece of common knowledge. If instead the gold answer's own text is literally contained in the
annotated fact, then a trivial string match from the fact to a choice would answer the item, which
would undercut that premise and leak the answer to any pipeline given the gold fact.

This census measures, over the Additional set, how often the normalized text of the **gold** answer
choice occurs as a substring of the normalized ``fact1``, and compares that to how often a
**distractor** choice does. A large gold-over-distractor asymmetry is a lexical answer leak; parity is
evidence the fact does not give the answer away by surface form. Substring containment is contiguous
and case/whitespace-normalized only (punctuation is kept), so the reported leak counts are a
conservative lower bound.

Apache-2.0.
"""


def normalize(s):
    """Collapse all whitespace runs to a single space, strip, and lowercase."""
    if s is None:
        return ""
    return " ".join(str(s).split()).lower()


def parse_row(obj):
    """Parse one OpenBookQA Additional jsonl object into a flat record.

    Raw shape: {"id", "question": {"stem", "choices": [{"text","label"}, ...]}, "answerKey", "fact1"}.
    A flat HuggingFace shape (question_stem + choices.{text,label} lists) is also accepted. Returns the
    normalized gold choice text (None if malformed), the normalized distractor texts, all normalized
    choice texts, and the normalized fact. A row whose answerKey matches no choice label is malformed.
    """
    q = obj.get("question")
    if isinstance(q, dict):
        stem = q.get("stem", "")
        choices = q.get("choices", []) or []
        texts = [c.get("text", "") for c in choices]
        labels = [c.get("label", "") for c in choices]
    else:
        stem = obj.get("question_stem", q if isinstance(q, str) else "")
        ch = obj.get("choices", {}) or {}
        texts = list(ch.get("text", []) or [])
        labels = list(ch.get("label", []) or [])
    key = obj.get("answerKey")
    key = None if key is None else str(key).strip()
    norm_by_label = {}
    norm_texts = []
    for lab, txt in zip(labels, texts):
        nt = normalize(txt)
        norm_by_label[str(lab).strip()] = nt
        norm_texts.append(nt)
    malformed = key is None or key not in norm_by_label
    gold_text = None if malformed else norm_by_label.get(key)
    if malformed:
        distractors = []
    else:
        distractors = [norm_by_label[l] for l in norm_by_label if l != key]
    return {
        "id": obj.get("id"),
        "stem": normalize(stem),
        "gold_text": gold_text,
        "distractor_texts": distractors,
        "choice_texts": norm_texts,
        "fact": normalize(obj.get("fact1")),
        "malformed": malformed,
    }


def fact_answer_stats(records, max_examples=5):
    """Count lexical answer leakage of the gold fact over a list of parsed records.

    For each non-malformed row: the gold answer is "in fact" if its normalized text is non-empty and a
    substring of the normalized fact; a distractor is "in fact" the same way. ``fact == a choice`` is a
    verbatim match of the whole fact to a choice text. Rates compare the per-question gold hit rate to
    the per-distractor hit rate (so option count is controlled for).
    """
    n_valid = 0
    n_malformed = 0
    n_gold_in_fact = 0
    n_any_distractor_in_fact = 0
    total_distractor_in_fact = 0
    n_distractors_total = 0
    n_fact_eq_a_choice = 0
    n_fact_eq_gold_choice = 0
    examples = []
    for r in records:
        if r["malformed"]:
            n_malformed += 1
            continue
        n_valid += 1
        fact = r["fact"]
        gold = r["gold_text"]
        gold_in = bool(gold) and gold in fact
        if gold_in:
            n_gold_in_fact += 1
            if len(examples) < max_examples:
                examples.append({"id": r["id"], "gold": gold, "fact": fact})
        d_hits = sum(1 for d in r["distractor_texts"] if d and d in fact)
        total_distractor_in_fact += d_hits
        n_distractors_total += len(r["distractor_texts"])
        if d_hits:
            n_any_distractor_in_fact += 1
        if fact and fact in r["choice_texts"]:
            n_fact_eq_a_choice += 1
            if fact == gold:
                n_fact_eq_gold_choice += 1
    gold_rate = (n_gold_in_fact / n_valid) if n_valid else 0.0
    distractor_rate = (total_distractor_in_fact / n_distractors_total) if n_distractors_total else 0.0
    return {
        "n_valid": n_valid,
        "n_malformed": n_malformed,
        "n_gold_in_fact": n_gold_in_fact,
        "n_any_distractor_in_fact": n_any_distractor_in_fact,
        "total_distractor_in_fact": total_distractor_in_fact,
        "n_distractors_total": n_distractors_total,
        "n_fact_eq_a_choice": n_fact_eq_a_choice,
        "n_fact_eq_gold_choice": n_fact_eq_gold_choice,
        "gold_coverage_rate": gold_rate,
        "distractor_coverage_rate": distractor_rate,
        "examples": examples,
    }


def flatten(stats):
    """Integer census keys only (drops rates and examples) for comparison against a frozen TARGET."""
    keep = (
        "n_valid", "n_malformed", "n_gold_in_fact", "n_any_distractor_in_fact",
        "total_distractor_in_fact", "n_distractors_total", "n_fact_eq_a_choice",
        "n_fact_eq_gold_choice",
    )
    return {k: stats[k] for k in keep}
