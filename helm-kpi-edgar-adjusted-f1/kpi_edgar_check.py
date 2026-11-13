#!/usr/bin/env python3
# Audit 116 (desk check): HELM's KPI-EDGAR metric, whose adjusted_macro_f1_score is the scenario's main metric.
# MV2 of Munim, Inc. -- made by AI agents working in MV2's name. Licence: Apache-2.0.
#
# The functions marked "transcribed" are copied from stanford-crfm/helm,
# src/helm/benchmark/metrics/kpi_edgar_metrics.py, as of commit 0d02c1b (2025-08-27, the last commit to touch
# the file). HELM is Apache-2.0. numpy.mean is replaced by a plain mean, the _compute_stats loop is split into
# pooled_counts + compute_stats, and the tag list is KPIEDGARScenario.TAG_DICT's keys. Standard library only.
import re
from dataclasses import dataclass

TAGS = ("kpi", "cy", "py", "py1")  # KPIEDGARScenario.TAG_DICT keys, in order
ENTITY_RE = r"(?:^|(?<=\],))([^\[\]]+)\[([0-9a-z]+)\](?:$|(?=,))"  # transcribed (_parse_entities)


@dataclass
class Entity:
    phrase: str
    tag: str


@dataclass
class Counts:
    num_overlap: int
    num_pred: int
    num_gold: int


@dataclass
class Rates:
    tp: float
    fn: float
    fp: float


def parse_entities(text):
    """Transcribed _parse_entities."""
    all_matches = re.findall(ENTITY_RE, text.strip())
    return [Entity(phrase=match[0].strip(), tag=match[1].strip()) for match in all_matches]


def compute_tag_to_words(entities):
    """Transcribed _compute_tag_to_words. A tag outside TAGS raises KeyError, as in HELM."""
    tag_to_words = {tag: set() for tag in TAGS}
    for entity in entities:
        for word in entity.phrase.split():
            tag_to_words[entity.tag].add(word)
    return tag_to_words


def compute_tag_to_counts(pred_entities, gold_entities):
    """Transcribed _compute_tag_to_counts."""
    tag_to_counts = {}
    pred_tag_to_words = compute_tag_to_words(pred_entities)
    gold_tag_to_words = compute_tag_to_words(gold_entities)
    for tag in TAGS:
        tag_to_counts[tag] = Counts(
            num_overlap=len(pred_tag_to_words[tag] & gold_tag_to_words[tag]),
            num_pred=len(pred_tag_to_words[tag]),
            num_gold=len(gold_tag_to_words[tag]),
        )
    return tag_to_counts


def counts_to_rates(counts, adjust):
    """Transcribed _counts_to_rates."""
    if adjust:
        return Rates(
            tp=counts.num_overlap / counts.num_gold if counts.num_gold > 0 else 0.0,
            fn=1 - (counts.num_overlap / counts.num_gold) if counts.num_gold > 0 else 0.0,
            fp=(counts.num_pred - counts.num_overlap) / counts.num_pred if counts.num_pred > 0 else 0.0,
        )
    return Rates(
        tp=counts.num_overlap,
        fn=counts.num_gold - counts.num_overlap,
        fp=counts.num_pred - counts.num_overlap,
    )


def compute_f1_score(rates):
    """Transcribed _compute_f1_score."""
    if rates.tp + rates.fp + rates.fn > 0:
        return (2 * rates.tp) / (2 * rates.tp + rates.fp + rates.fn)
    return 0.0


def pooled_counts(pred_gold_pairs):
    """First half of transcribed _compute_stats: per-tag counts summed over all instances."""
    tag_to_counts = {tag: Counts(0, 0, 0) for tag in TAGS}
    for pred_text, gold_text in pred_gold_pairs:
        pred_entities = parse_entities(pred_text)
        gold_entities = parse_entities(gold_text)
        instance = compute_tag_to_counts(pred_entities=pred_entities, gold_entities=gold_entities)
        for tag, c in instance.items():
            tag_to_counts[tag].num_overlap += c.num_overlap
            tag_to_counts[tag].num_pred += c.num_pred
            tag_to_counts[tag].num_gold += c.num_gold
    return tag_to_counts


def per_tag_scores(pred_gold_pairs):
    """Not in HELM: the per-tag F1 values that HELM averages."""
    out = {}
    for tag, c in pooled_counts(pred_gold_pairs).items():
        out[tag] = {
            "word": compute_f1_score(counts_to_rates(c, adjust=False)),
            "adjusted": compute_f1_score(counts_to_rates(c, adjust=True)),
            "overlap": c.num_overlap,
            "pred": c.num_pred,
            "gold": c.num_gold,
        }
    return out


def compute_stats(pred_gold_pairs):
    """Second half of transcribed _compute_stats: macro means over the four tags."""
    tag_to_counts = pooled_counts(pred_gold_pairs)
    word = [compute_f1_score(counts_to_rates(c, adjust=False)) for c in tag_to_counts.values()]
    adjusted = [compute_f1_score(counts_to_rates(c, adjust=True)) for c in tag_to_counts.values()]
    return {
        "word_macro_f1_score": sum(word) / len(word),
        "adjusted_macro_f1_score": sum(adjusted) / len(adjusted),
    }


def helm_pairs(records):
    """What HELM's _request_states_to_pred_gold_pairs builds: (reference text, completion text).

    records: list of (gold_text, completion_text). _compute_stats then reads each pair as (pred, gold)."""
    return [(gold, pred) for gold, pred in records]


def fixed_pairs(records):
    """The order PR #4350 proposes: (completion text, reference text)."""
    return [(pred, gold) for gold, pred in records]


def score(records, orientation="helm"):
    pairs = helm_pairs(records) if orientation == "helm" else fixed_pairs(records)
    return compute_stats(pairs)


def tag_scores(records, orientation="helm"):
    pairs = helm_pairs(records) if orientation == "helm" else fixed_pairs(records)
    return per_tag_scores(pairs)


# Closed forms for one tag, with pooled recall r = O/G and precision p = O/P (G > 0 and P > 0).
def adjusted_fixed(r, p):
    """Adjusted F1 in PR #4350's order: tp = r, fn = 1 - r, fp = 1 - p."""
    return 2 * r / (2 + r - p)


def adjusted_helm(r, p):
    """Adjusted F1 in HELM's current order (prediction and gold swapped): r and p trade places."""
    return 2 * p / (2 + p - r)


def word_f1(r, p):
    """Plain word F1, 2O/(P+G), the same in both orders."""
    return 0.0 if r + p == 0 else 2 * p * r / (p + r)


def copy_answer(passage):
    """An answer that repeats the whole sentence under each of the four tags."""
    return ", ".join("%s [%s]" % (passage, tag) for tag in TAGS)


EXAMPLES = [
    ("issue_4348", "revenue increased [kpi], 100 [cy], 90 [py]", "revenue [kpi], 100 [cy]"),
    ("copy_sentence", "Revenue [kpi], 100 [cy], 90 [py], 80 [py1]", copy_answer("Revenue was 100 , 90 and 80 .")),
    ("one_of_three_kpi_words", "total net revenue [kpi], 100 [cy], 90 [py], 80 [py1]",
     "revenue [kpi], 100 [cy], 90 [py], 80 [py1]"),
    ("two_extra_kpi_words", "total net revenue [kpi], 100 [cy], 90 [py], 80 [py1]",
     "the total net revenue was [kpi], 100 [cy], 90 [py], 80 [py1]"),
]


def main():
    print("example | HELM adjusted (current) | adjusted (PR #4350 order) | word F1")
    for name, gold, pred in EXAMPLES:
        h = score([(gold, pred)], "helm")
        f = score([(gold, pred)], "fixed")
        print("%s | %.6f | %.6f | %.6f" % (name, h["adjusted_macro_f1_score"], f["adjusted_macro_f1_score"],
                                            f["word_macro_f1_score"]))
    print("floor per tag at p = 1 (current order) or r = 1 (PR #4350 order), r or p -> 0: %.6f" %
          adjusted_helm(1e-9, 1.0))
    try:
        score([("revenue [kpi], 100 [cy]", "revenue [kpi], 2021 [year]")], "helm")
        print("unknown tag: no error")
    except KeyError as e:
        print("unknown tag: KeyError %s (the whole run's metric step fails)" % e)


if __name__ == "__main__":
    main()
