# SPDX-License-Identifier: Apache-2.0
# Audit 118 (pre-registered) by MV2 of Munim, Inc. Made with AI agents working in MV2's name.
#
# normalize_text, quasi_exact_match and quasi_prefix_exact_match are transcribed from HELM's
# src/helm/benchmark/metrics/evaluate_reference_metrics.py (stanford-crfm/helm main, read 2026-11-13).
# HELM is Apache-2.0 (Stanford CRFM).
"""VHELM's Unicorn scenario: how much of each published score needs the image?

HELM's unicorn run spec asks for "a yes/no or numerical answer", allows max_tokens=1 and scores
quasi_prefix_exact_match. In the Unicorn benchmark's OODCV-VQA set (Tu et al., arXiv 2311.16101, Table 2)
every yes/no gold is "Yes", and the counting questions about unicorns ("How many unicorns are there in the
image?") are, by construction, answered 0. Those questions can be answered from the question text alone.
This module classifies each question, transcribes HELM's scorer, and summarises one run.
"""
import hashlib
import math
import re
import string
from collections import Counter
from fractions import Fraction

STAT = "quasi_prefix_exact_match"
SUBJECTS = ("OODCV-VQA", "Sketchy-VQA")
CLASSES = ("presence", "unicorn", "count", "sketch", "other")
KINDS = ("yesno", "number", "empty", "other")


# ---------------- transcribed from HELM (Apache-2.0) ----------------
def normalize_text(text, should_remove_articles=True):
    """Lower text and remove punctuation, articles and extra whitespace."""

    def remove_articles(text):
        return re.sub(r"\b(a|an|the)\b", " ", text)

    def white_space_fix(text):
        return " ".join(text.split())

    def remove_punc(text):
        exclude = set(string.punctuation)
        return "".join(ch for ch in text if ch not in exclude)

    def lower(text):
        return text.lower()

    normalized_text = remove_punc(lower(text))
    if should_remove_articles:
        normalized_text = remove_articles(normalized_text)
    return white_space_fix(normalized_text)


def quasi_exact_match(gold, pred):
    if not pred:
        return 0
    return 1 if normalize_text(gold) == normalize_text(pred) else 0


def quasi_prefix_exact_match(gold, pred):
    if not pred:
        return 0
    return 1 if normalize_text(pred).startswith(normalize_text(gold)) else 0


# ---------------- ours ----------------
_PRESENCE = re.compile(r"^is there an? .+ in the image\?$", re.I)
_COUNT = re.compile(r"^how many .+ in the image\?$", re.I)


def question_class(subject, question):
    """presence / unicorn / count for OODCV-VQA's two templates; sketch for every Sketchy-VQA question."""
    q = " ".join((question or "").split())
    if subject.startswith("Sketchy"):
        return "sketch"
    if _COUNT.match(q):
        return "unicorn" if "unicorn" in q.lower() else "count"
    if _PRESENCE.match(q):
        return "presence"
    return "other"


def answer_kind(pred):
    """yesno / number / empty / other, read from HELM's normalised text (raw blank first)."""
    if not (pred or "").strip():
        return "empty"
    n = normalize_text(pred)
    if n in ("yes", "no"):
        return "yesno"
    if re.fullmatch(r"[0-9]+", n):
        return "number"
    return "other"


def question_of(instance):
    """The text/plain media object of a multimodal instance (falls back to input.text)."""
    inp = (instance or {}).get("input") or {}
    mc = inp.get("multimedia_content") or {}
    for mo in mc.get("media_objects") or []:
        if isinstance(mo, dict) and str(mo.get("content_type", "")).startswith("text") and mo.get("text"):
            return mo["text"]
    return inp.get("text") or ""


def gold_of(instance):
    """Text of the first reference tagged 'correct' (None when there is none)."""
    for ref in (instance or {}).get("references") or []:
        if isinstance(ref, dict) and "correct" in (ref.get("tags") or []):
            return (ref.get("output") or {}).get("text")
    return None


def subject_of(run_name):
    i = run_name.find("subject=")
    return run_name[i + len("subject="):].split(",")[0] if i >= 0 else ""


def model_of(run_name):
    i = run_name.find("model=")
    return run_name[i + len("model="):].split(",")[0] if i >= 0 else ""


def is_number(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool) and not (isinstance(v, float) and math.isnan(v))


def stat_entry(stats, name, split="test"):
    """{count, sum, mean} of the unperturbed stat `name` on `split` in a HELM stats.json list (None when absent)."""
    for s in stats or []:
        if not isinstance(s, dict):
            continue
        nm = s.get("name") or {}
        if (nm.get("name") == name and nm.get("split") == split and nm.get("perturbation") is None
                and nm.get("sub_split") is None):
            return {"count": s.get("count"), "sum": s.get("sum"), "mean": s.get("mean")}
    return None


def instance_map(subject, instances):
    """{test id: (class, gold)}."""
    out = {}
    for i in instances or []:
        if isinstance(i, dict) and i.get("split") == "test":
            out[i.get("id")] = (question_class(subject, question_of(i)), gold_of(i))
    return out


def best_constant(golds):
    """Most common gold (ties: the smallest string), None for an empty list."""
    c = Counter(g for g in golds if g is not None)
    if not c:
        return None
    top = max(c.values())
    return min(g for g, v in c.items() if v == top)


def blind_answer(cls, best_count, best_sketch):
    """The text-only answer: presence -> Yes, unicorn -> 0, count -> best constant count, sketch -> best constant."""
    return {"presence": "Yes", "unicorn": "0", "count": best_count, "sketch": best_sketch}.get(cls) or ""


def blind_score(imap, best_count, best_sketch):
    """HELM's metric on the text-only answers, as an exact Fraction over the instances (None when empty)."""
    if not imap:
        return None
    s = sum(quasi_prefix_exact_match(g or "", blind_answer(c, best_count, best_sketch)) for c, g in imap.values())
    return Fraction(s, len(imap))


def summarize_run(preds, imap):
    """Census of one run's display_predictions (unperturbed, test ids only, first record per instance)."""
    counts = {"n_records": 0, "perturbed": 0, "not_test": 0, "duplicate": 0, "kept": 0,
              "stored_missing": 0, "mismatch": 0, "prefix_only": 0, "credit": 0}
    by_class = {c: {"n": 0, "credit": 0, "exact": 0} for c in CLASSES}
    kinds = {k: 0 for k in KINDS}
    answers = Counter()
    seen = set()
    examples = {"prefix_only": [], "other": []}
    for r in preds or []:
        if not isinstance(r, dict):
            continue
        counts["n_records"] += 1
        if r.get("perturbation") is not None:
            counts["perturbed"] += 1
            continue
        iid = r.get("instance_id")
        if iid not in imap:
            counts["not_test"] += 1
            continue
        if iid in seen:
            counts["duplicate"] += 1
            continue
        seen.add(iid)
        counts["kept"] += 1
        cls, gold = imap[iid]
        gold = gold or ""
        pred = r.get("predicted_text") or ""
        ours = quasi_prefix_exact_match(gold, pred)
        v = (r.get("stats") or {}).get(STAT)
        if not is_number(v):
            counts["stored_missing"] += 1
            v = 0
        elif abs(v - ours) > 1e-9:
            counts["mismatch"] += 1
        exact = quasi_exact_match(gold, pred)
        credit = 1 if v >= 0.5 else 0
        counts["credit"] += credit
        if ours == 1 and exact == 0:
            counts["prefix_only"] += 1
            if len(examples["prefix_only"]) < 3:
                examples["prefix_only"].append((iid, gold, pred[:40]))
        k = answer_kind(pred)
        kinds[k] += 1
        if k == "other" and len(examples["other"]) < 3:
            examples["other"].append((iid, gold, pred[:40]))
        answers[normalize_text(pred) if k in ("yesno", "number") else "<" + k + ">"] += 1
        b = by_class[cls]
        b["n"] += 1
        b["credit"] += credit
        b["exact"] += exact
    return {"counts": counts, "by_class": by_class, "kinds": kinds, "answers": dict(answers), "examples": examples}


def acc(b):
    return Fraction(b["credit"], b["n"]) if b and b["n"] else None


def ranks_high(values):
    """Higher is better: rank = 1 + the number of entries strictly higher (exact values)."""
    return {k: 1 + sum(1 for w in values.values() if w > v) for k, v in values.items()}


def kendall_tau_b(xs, ys):
    """Kendall's tau-b of two equal-length sequences (None when either is constant or shorter than 2)."""
    n = len(xs)
    c = d = tx = ty = 0
    for i in range(n):
        for j in range(i + 1, n):
            dx = (xs[i] > xs[j]) - (xs[i] < xs[j])
            dy = (ys[i] > ys[j]) - (ys[i] < ys[j])
            if dx == 0:
                tx += 1
            if dy == 0:
                ty += 1
            if dx and dy:
                if dx == dy:
                    c += 1
                else:
                    d += 1
    n0 = n * (n - 1) // 2
    den = (n0 - tx) * (n0 - ty)
    return (c - d) / math.sqrt(den) if den > 0 else None


def stable_hash(text):
    return int(hashlib.sha256(text.encode("utf-8")).hexdigest()[:12], 16)


# ---------------- Verdicts ----------------
def verdicts(s):
    """The eight pre-registered predictions (True = HELD, False = FAILED, None = not gradable)."""
    def ge(a, b):
        return None if a is None else a >= b

    pres, uni, cnt = s.get("pooled_presence"), s.get("pooled_unicorn"), s.get("pooled_count")
    p3 = None if None in (pres, uni, cnt) else (pres >= Fraction(95, 100) and uni >= Fraction(9, 10)
                                                and cnt <= Fraction(7, 10))
    credits = s.get("pooled_credits") or 0
    p5 = None if not credits else s["pooled_prefix_only"] * 200 < credits
    lead = s.get("leader_changes")
    return {
        "P1": (s["runs_listed"] == 102 and s["runs_included"] * 100 >= 95 * s["runs_listed"]
               and s["ids_oodcv"] >= 900 and s["ids_sketchy"] >= 900),
        "P2": ge(s.get("below_blind_oodcv"), 5),
        "P3": p3,
        "P4": ge(s.get("movers_count"), 10),
        "P5": p5,
        "P6": ge(s.get("runs_nonanswer5"), 3),
        "P7": ge(s.get("sketchy_one_answer80"), 1),
        "P8": None if lead is None else bool(lead),
    }


def verdict_word(v):
    return "NOT GRADED" if v is None else ("HELD" if v else "FAILED")
