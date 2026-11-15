# SPDX-License-Identifier: Apache-2.0
"""Audit 122: how VHELM credits open-ended short answers (GQA, VQAv2, VizWiz).

VHELM (HELM's vision-language leaderboard, run suite v2.1.2) scores GQA, VQAv2 (vqa_base) and VizWiz with
quasi_prefix_exact_match as the MAIN metric: an answer scores 1 when its normalised text STARTS WITH the normalised
text of ANY reference tagged correct (HELM takes the max over references). normalize_text lower-cases, removes ASCII
punctuation and the English articles a/an/the, and collapses whitespace. The references are:
  * GQA: the short answer and the full-sentence answer;
  * VQAv2: all 10 annotator answers, not de-duplicated (an answer one annotator gave is a correct reference);
  * VizWiz: the distinct answers annotators gave with confidence 'yes'.
Graders per archived first-trial record: H = HELM's score (transcribed from stanford-crfm/helm, Apache-2.0);
Q = quasi_exact_match against any reference (no prefix credit); C (VQAv2 only) = a VQA-style consensus accuracy:
m = number of the 10 annotator answers equal to the answer after HELM's normalize_text, C = leave-one-annotator-out
mean of min(1, matches / 3). C uses HELM's normalisation, not the official VQA answer processing.
Standard library only. Apache-2.0. Made with AI agents working in MV2's name (MV2 of Munim, Inc.).
"""
import re
import string
from fractions import Fraction

STAT = "quasi_prefix_exact_match"
QSTAT = "quasi_exact_match"
CLASSES = ("match", "word_prefix", "mid_word", "empty_ref")
MARKUP = re.compile(r"</?(?:ref|box|quad)>")

# ----- HELM's reference metrics, transcribed (src/helm/benchmark/metrics/evaluate_reference_metrics.py) -----


def normalize_text(text, should_remove_articles=True):
    """Lower text and remove punctuation, articles and extra whitespace (HELM, from the QuAC scorer)."""

    def remove_articles(t):
        return re.sub(r"\b(a|an|the)\b", " ", t)

    def white_space_fix(t):
        return " ".join(t.split())

    def remove_punc(t):
        exclude = set(string.punctuation)
        return "".join(ch for ch in t if ch not in exclude)

    def lower(t):
        return t.lower()

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


def helm_pred(text):
    """HELM strips each completion before scoring."""
    return (text or "").strip()


# ----- Graders -----

def credit_class(refs, pred):
    """(H, Q, class). H = max over refs of quasi_prefix_exact_match, Q = max of quasi_exact_match. The class of a
    credit (None when H is 0), the first that applies: match (Q is 1); word_prefix (the answer's normalised text
    starts with a non-empty normalised reference followed by a space, e.g. 'no, it is not' for 'no'); mid_word (it
    starts with a non-empty normalised reference whose last word it continues, e.g. 'carpet' for 'car'); empty_ref
    (only a reference that normalises to '' credits it)."""
    p = helm_pred(pred)
    h = max((quasi_prefix_exact_match(r, p) for r in refs), default=0)
    q = max((quasi_exact_match(r, p) for r in refs), default=0)
    if not h:
        return h, q, None
    if q:
        return h, q, "match"
    npred = normalize_text(p)
    nrefs = [normalize_text(r) for r in refs]
    if any(nr and npred.startswith(nr + " ") for nr in nrefs):
        return h, q, "word_prefix"
    if any(nr and npred.startswith(nr) for nr in nrefs):
        return h, q, "mid_word"
    return h, q, "empty_ref"


def match_count(refs, pred):
    """Number of references equal to the answer after HELM's normalize_text (0 for an empty answer)."""
    p = helm_pred(pred)
    return sum(quasi_exact_match(r, p) for r in refs)


def vqa_consensus(m, n):
    """Leave-one-annotator-out mean of min(1, matches / 3) over n annotators, m of whom match; None unless n == 10."""
    if n != 10:
        return None
    if m == 0:
        return Fraction(0)
    return (m * min(Fraction(1), Fraction(m - 1, 3)) + (n - m) * min(Fraction(1), Fraction(m, 3))) / n


def has_markup(pred):
    """True when the answer carries grounding markup such as <ref>...</ref><box>...</box>."""
    return bool(MARKUP.search(pred or ""))


# ----- Run files -----

def run_field(run, key):
    """'vqa:model=x,groups=y' -> value of `key` (None if absent)."""
    body = run.split(":", 1)[1] if ":" in run else run
    for part in body.split(","):
        if part.startswith(key + "="):
            return part[len(key) + 1:]
    return None


def stat_mean(stats, split, name):
    """Mean of the unperturbed stats.json entry with this metric name and split; None if absent."""
    for e in stats or []:
        n = e.get("name") or {}
        if n.get("name") == name and n.get("split") == split and not n.get("perturbation"):
            return e.get("mean")
    return None


def instance_map(inst, split):
    """{id: [correct reference texts]} for unperturbed main-split instances, and the number of perturbed ones skipped."""
    out, perturbed = {}, 0
    for it in inst or []:
        if not isinstance(it, dict) or it.get("split") != split:
            continue
        if it.get("perturbation"):
            perturbed += 1
            continue
        refs = [((r.get("output") or {}).get("text") or "") for r in (it.get("references") or [])
                if "correct" in (r.get("tags") or [])]
        out[it.get("id")] = refs
    return out, perturbed


def new_sub():
    return {"n": 0, "h": 0, "q": 0, "cls": {c: 0 for c in CLASSES}, "markup": 0, "markup_h": 0,
            "c_sum": Fraction(0), "c_n": 0, "minority": 0, "zero_match": 0,
            "m_hist": {"0": 0, "1": 0, "2": 0, "3": 0, "4+": 0}}


def summarize_run(preds, imap, consensus=False):
    """Grade every first-trial unperturbed record. Returns (counts, sub, examples). examples holds
    (instance id, class, matched-reference count) for mid_word / empty_ref credits and minority credits."""
    c = {"n_pred": 0, "other_trial": 0, "perturbed": 0, "no_instance": 0, "duplicate": 0, "scored": 0,
         "rec_checked": 0, "rec_agree": 0}
    s = new_sub()
    seen, examples = set(), []
    for p in preds or []:
        if not isinstance(p, dict):
            continue
        c["n_pred"] += 1
        if p.get("train_trial_index", 0) != 0:
            c["other_trial"] += 1
            continue
        if p.get("perturbation"):
            c["perturbed"] += 1
            continue
        iid = p.get("instance_id")
        refs = imap.get(iid)
        if refs is None:
            c["no_instance"] += 1
            continue
        if iid in seen:
            c["duplicate"] += 1
            continue
        seen.add(iid)
        pred = p.get("predicted_text")
        h, q, cls = credit_class(refs, pred)
        c["scored"] += 1
        stored = (p.get("stats") or {}).get(STAT)
        if stored is not None:
            c["rec_checked"] += 1
            c["rec_agree"] += 1 if float(stored) == float(h) else 0
        s["n"] += 1
        s["h"] += h
        s["q"] += q
        if has_markup(pred):
            s["markup"] += 1
            s["markup_h"] += h
        m = match_count(refs, pred)
        if cls:
            s["cls"][cls] += 1
            s["m_hist"][str(m) if m < 4 else "4+"] += 1
            if m == 0:
                s["zero_match"] += 1
            elif m <= 2:
                s["minority"] += 1
        if consensus:
            cv = vqa_consensus(m, len(refs))
            if cv is not None:
                s["c_sum"] += cv
                s["c_n"] += 1
        if cls in ("mid_word", "empty_ref") or (cls and 1 <= m <= 2 and consensus):
            examples.append((iid, cls, m))
    return c, s, examples


# ----- Ranks and rank agreement (as audits 91, 92, 121) -----

def min_ranks(acc):
    """acc {model: value} -> {model: 1 + number of models with a strictly higher value}."""
    return {m: 1 + sum(1 for o in acc if acc[o] > acc[m]) for m in acc}


def kendall_tau_b(xs, ys):
    """Kendall's tau-b of two equal-length lists; None when either list is constant."""
    conc = disc = tx = ty = 0
    n = len(xs)
    for i in range(n):
        for j in range(i + 1, n):
            dx = (xs[i] > xs[j]) - (xs[i] < xs[j])
            dy = (ys[i] > ys[j]) - (ys[i] < ys[j])
            if dx == 0 and dy == 0:
                continue
            if dx == 0:
                tx += 1
            elif dy == 0:
                ty += 1
            elif dx == dy:
                conc += 1
            else:
                disc += 1
    denom = ((conc + disc + tx) * (conc + disc + ty)) ** 0.5
    return (conc - disc) / denom if denom else None


# ----- Pre-registered verdicts -----

THRESHOLDS = {"P1_share": Fraction(99, 100), "P2_pct": 2, "P3_diff": Fraction(3, 100), "P4_movers": 1,
              "P5_pct": 1, "P6_share": Fraction(5, 100), "P6_models": 3, "P7_share": Fraction(9, 10), "P8_pct": 1}


def verdicts(st, th=THRESHOLDS):
    """st: {'fam_inc': {fam: (included, listed)}, 'vqa_credits', 'vqa_minority', 'vqa_zero_match': int,
    'vqa_median_diff': Fraction or None, 'vqa_movers': int, 'gqa_credits', 'gqa_mid': int, 'gqa_word_models': int,
    'qwen_markup': {fam: (markup, n)}} -> {name: bool}."""
    p1 = all(n > 0 and Fraction(i, n) >= th["P1_share"] for i, n in st["fam_inc"].values())
    qm = st["qwen_markup"]
    p7 = all(f in qm and qm[f][1] > 0 and Fraction(qm[f][0], qm[f][1]) >= th["P7_share"] for f in ("vqa", "viz_wiz"))
    vc = st["vqa_credits"]
    return {
        "P1_reproduced": p1,
        "P2_vqa_minority_credits": vc > 0 and st["vqa_minority"] * 100 >= th["P2_pct"] * vc,
        "P3_vqa_median_gap": st["vqa_median_diff"] is not None and st["vqa_median_diff"] >= th["P3_diff"],
        "P4_vqa_rank_moves": st["vqa_movers"] >= th["P4_movers"],
        "P5_gqa_mid_word_rare": st["gqa_credits"] > 0 and st["gqa_mid"] * 100 < th["P5_pct"] * st["gqa_credits"],
        "P6_gqa_sentence_credit": st["gqa_word_models"] >= th["P6_models"],
        "P7_qwen_vl_chat_markup": p7,
        "P8_vqa_prefix_only_rare": vc > 0 and st["vqa_zero_match"] * 100 < th["P8_pct"] * vc,
    }


def verdict_word(v):
    return "HELD" if v else "FAILED"
