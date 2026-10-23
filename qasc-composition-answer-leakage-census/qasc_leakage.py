"""Does QASC's annotation leak the answer, and does the *composed* fact leak it more than either single fact?

Part of MV2's eval-reliability-audits catalogue (Munim, Inc.). This research is carried out by
AI agents working in MV2's name.

QASC (Khot et al., 2020) is an 8-way multiple-choice science benchmark built around *sentence
composition*: every annotated question carries two retrieved facts, ``fact1`` and ``fact2``, that must
be composed to answer it, plus a ``combinedfact`` -- a single sentence stating that composition. The
benchmark's premise is that neither single fact is sufficient; the answer only follows from joining the
two. That makes a specific, falsifiable leakage question: how often does the gold answer's text appear
in ``combinedfact`` (the composition), and does that happen *more* than in either single fact ``fact1``
or ``fact2`` on its own? The clean control, as for the OpenBookQA and SciQ leakage audits, is the
distractors: a leak is only answer-specific if the gold answer is contained far more often than a wrong
choice is.

"In fact" is contiguous substring containment after whitespace/case normalization (punctuation kept),
so every reported rate is a conservative lower bound on lexical surface overlap.

Apache-2.0.
"""

FACT_FIELDS = ("fact1", "fact2", "combinedfact")


def normalize(s):
    """Collapse all whitespace runs to a single space, strip, and lowercase."""
    if s is None:
        return ""
    return " ".join(str(s).split()).lower()


def _extract_choices(obj):
    """Return a list of (label, normalized_text) over the several QASC serializations.

    Handles: the original nested shape ``{"question": {"stem", "choices": [{"text","label"}, ...]}}``,
    a flat ``{"choices": [{"text","label"}, ...]}``, and the HuggingFace struct-of-lists
    ``{"choices": {"text": [...], "label": [...]}}``.
    """
    pairs = []
    q = obj.get("question")
    choices = None
    if isinstance(q, dict) and "choices" in q:
        choices = q.get("choices")
    if choices is None:
        choices = obj.get("choices")
    if isinstance(choices, list):
        for c in choices:
            if isinstance(c, dict):
                pairs.append((str(c.get("label", "")), normalize(c.get("text"))))
    elif isinstance(choices, dict):
        labels = choices.get("label", []) or []
        texts = choices.get("text", []) or []
        for lab, txt in zip(labels, texts):
            pairs.append((str(lab), normalize(txt)))
    return pairs


def parse_row(obj):
    """Parse one QASC record into a flat leakage record.

    ``annotated`` is True when a non-empty ``answerKey`` is present (train/dev; the public test split
    has neither answer key nor facts). Among annotated rows, if the ``answerKey`` matches no choice
    label the row is malformed (``gold_text`` is None) and excluded. ``gold_text`` is the normalized
    text of the choice whose label equals ``answerKey``; ``distractor_texts`` are the other choices.
    ``facts`` holds the normalized ``fact1``, ``fact2`` and ``combinedfact``.
    """
    answer_key = obj.get("answerKey")
    has_key = answer_key is not None and str(answer_key).strip() != ""
    pairs = _extract_choices(obj)
    gold = None
    if has_key:
        for lab, txt in pairs:
            if lab == str(answer_key):
                gold = txt
                break
    distractors = [txt for lab, txt in pairs if not (has_key and lab == str(answer_key))]
    facts = {f: normalize(obj.get(f)) for f in FACT_FIELDS}
    return {
        "has_key": has_key,
        "annotated": has_key,
        "gold_text": gold,
        "distractor_texts": distractors,
        "facts": facts,
    }


def leakage_stats(records, max_examples=5):
    """Count lexical answer leakage of fact1/fact2/combinedfact over a list of parsed records.

    A valid row is an annotated row whose answerKey matched a choice. For each fact field the gold
    answer is "in field" when its non-empty normalized text is a substring of the normalized field, and
    each distractor is tested the same way. ``n_gold_in_either_single`` counts valid rows whose gold is
    in fact1 or fact2; ``n_gold_in_combined_not_single`` counts valid rows whose gold is in the
    combinedfact but in *neither* single fact -- the cases where the composition, and only the
    composition, spells out the answer. Example rows capture those composition-only leaks.
    """
    n_valid = 0
    n_unannotated = 0
    n_malformed = 0
    n_distractors_total = 0
    gold_in = {f: 0 for f in FACT_FIELDS}
    dist_in = {f: 0 for f in FACT_FIELDS}
    n_gold_in_either_single = 0
    n_gold_in_combined_not_single = 0
    examples = []
    for r in records:
        if not r["annotated"]:
            n_unannotated += 1
            continue
        if r["gold_text"] is None:
            n_malformed += 1
            continue
        n_valid += 1
        gold = r["gold_text"]
        facts = r["facts"]
        dists = r["distractor_texts"]
        n_distractors_total += len(dists)
        in_field = {}
        for f in FACT_FIELDS:
            fv = facts[f]
            g_in = bool(gold) and gold in fv
            in_field[f] = g_in
            if g_in:
                gold_in[f] += 1
            dist_in[f] += sum(1 for d in dists if d and d in fv)
        in_single = in_field["fact1"] or in_field["fact2"]
        if in_single:
            n_gold_in_either_single += 1
        if in_field["combinedfact"] and not in_single:
            n_gold_in_combined_not_single += 1
            if len(examples) < max_examples:
                examples.append({
                    "gold": gold,
                    "fact1": facts["fact1"][:120],
                    "fact2": facts["fact2"][:120],
                    "combinedfact": facts["combinedfact"][:160],
                })

    def rate(n, d):
        return (n / d) if d else 0.0

    out = {
        "n_valid": n_valid,
        "n_unannotated": n_unannotated,
        "n_malformed": n_malformed,
        "n_distractors_total": n_distractors_total,
        "gold_in_fact1": gold_in["fact1"],
        "gold_in_fact2": gold_in["fact2"],
        "gold_in_combinedfact": gold_in["combinedfact"],
        "dist_in_fact1": dist_in["fact1"],
        "dist_in_fact2": dist_in["fact2"],
        "dist_in_combinedfact": dist_in["combinedfact"],
        "n_gold_in_either_single": n_gold_in_either_single,
        "n_gold_in_combined_not_single": n_gold_in_combined_not_single,
        "gold_rate_fact1": rate(gold_in["fact1"], n_valid),
        "gold_rate_fact2": rate(gold_in["fact2"], n_valid),
        "gold_rate_combinedfact": rate(gold_in["combinedfact"], n_valid),
        "dist_rate_fact1": rate(dist_in["fact1"], n_distractors_total),
        "dist_rate_fact2": rate(dist_in["fact2"], n_distractors_total),
        "dist_rate_combinedfact": rate(dist_in["combinedfact"], n_distractors_total),
        "examples": examples,
    }
    return out


_FLAT_KEYS = (
    "n_valid", "n_unannotated", "n_malformed", "n_distractors_total",
    "gold_in_fact1", "gold_in_fact2", "gold_in_combinedfact",
    "dist_in_fact1", "dist_in_fact2", "dist_in_combinedfact",
    "n_gold_in_either_single", "n_gold_in_combined_not_single",
)


def flatten(stats):
    """Integer census keys only (drops rates and examples) for comparison against a frozen TARGET."""
    return {k: stats[k] for k in _FLAT_KEYS}
