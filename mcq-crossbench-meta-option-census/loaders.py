"""Per-schema row shaping for audit 57. Pure standard library (no pyarrow) so it is unit-testable in isolation.

Each function turns one raw parquet record into the generic census tuple parts (labels, texts, answer_key) that
position_census / meta_option consume. Downstream, question_validity() turns a goldless row (empty answer) into
'bad_key' and a malformed row into 'degenerate'; nothing here raises on empty or None input.

Apache-2.0.
"""


def _texts(seq):
    return [("" if t is None else str(t)) for t in seq]


def shape_choices_struct(choices, answer_key):
    """ARC / CommonsenseQA: `choices` is a struct of parallel lists {"text": [...], "label": [...]}.

    Returns (labels, texts, answer_key_str). Labels are kept verbatim (e.g. "A".."E" or "1".."4"); the gold
    position is labels.index(answer_key) downstream.
    """
    labels = [("" if x is None else str(x)) for x in choices["label"]]
    texts = _texts(choices["text"])
    return labels, texts, ("" if answer_key is None else str(answer_key))


def shape_endings(endings, label):
    """HellaSwag: `endings` is a list[str]; `label` is the gold index as a string ("0".."3").

    Returns (labels, texts, answer_key_str) with labels synthesised as "0".."k-1".
    """
    texts = _texts(endings)
    labels = [str(i) for i in range(len(texts))]
    return labels, texts, ("" if label is None else str(label))
