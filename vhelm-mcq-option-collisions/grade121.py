# SPDX-License-Identifier: Apache-2.0
"""Audit 121: does HELM's option-text scoring (HELM issue #4358) reach VHELM's published multiple-choice scores?

VHELM (HELM's vision-language leaderboard, run suite v2.1.2) scores A-OKVQA (English and five augmented variants:
Chinese, Hindi, Spanish and Swahili machine translation, an AAVE dialect rewrite and a robustness group), MMMU
(multiple-choice) and SEED-Bench with the multiple_choice_joint adapter and quasi_prefix_exact_match as the MAIN
metric. The adapter maps the answer letter to the TEXT of that option and the metric compares that text with the gold
option's text after normalize_text (lower case, ASCII punctuation removed, English articles a/an/the removed):
  * a wrong option is credited when its normalised text equals the gold's or merely STARTS WITH it;
  * a gold option whose text normalises to '' (for example an option that is just the letter 'A', or 'The') credits
    every non-empty option.
Graders, per archived first-trial record: H = HELM's score (letter -> option text -> quasi_prefix_exact_match,
transcribed from stanford-crfm/helm, Apache-2.0); I = option identity (1 when the letter names the gold option).
For augmented runs the published cell is HELM's per-instance WORST case over the original and perturbed copies.
Standard library only. Apache-2.0. Made with AI agents working in MV2's name (MV2 of Munim, Inc.).
"""
import hashlib
import re
import string
from fractions import Fraction

LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
STAT = "quasi_prefix_exact_match"
OVER_CLASSES = ("gold_empty", "identical", "quasi_only", "prefix_only")

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


def exact_match(gold, pred):
    if not pred:
        return 0
    return 1 if gold.strip() == pred.strip() else 0


def quasi_exact_match(gold, pred):
    if not pred:
        return 0
    return 1 if normalize_text(gold) == normalize_text(pred) else 0


def quasi_prefix_exact_match(gold, pred):
    if not pred:
        return 0
    return 1 if normalize_text(pred).startswith(normalize_text(gold)) else 0


# ----- The letter mapping (multiple_choice_joint: 'A', 'B', ... in reference order; completion.strip()) -----

def letter_index(pred, k):
    """Index of the option HELM's output_mapping gives for this output, or None when the stripped output is not
    exactly one of the first k capital letters."""
    s = (pred or "").strip()
    if len(s) == 1 and s in LETTERS[:k]:
        return LETTERS.index(s)
    return None


def over_class(gold, mapped):
    """Why a wrong option was credited: the first of gold_empty / identical / quasi_only / prefix_only that applies."""
    if normalize_text(gold) == "":
        return "gold_empty"
    if exact_match(gold, mapped):
        return "identical"
    if quasi_exact_match(gold, mapped):
        return "quasi_only"
    return "prefix_only"


def grade(opts, gold_i, pred):
    """H, I, the mapped option text and the flip class ('over:<class>' when H 1 and I 0, 'under' when H 0, I 1)."""
    idx = letter_index(pred, len(opts))
    if idx is None:
        return {"idx": None, "h": 0, "i": 0, "cls": None, "mapped": None}
    mapped = opts[idx]
    gold = opts[gold_i]
    h = quasi_prefix_exact_match(gold, mapped)
    i = 1 if idx == gold_i else 0
    cls = None
    if h == 1 and i == 0:
        cls = "over:" + over_class(gold, mapped)
    elif h == 0 and i == 1:
        cls = "under"
    return {"idx": idx, "h": h, "i": i, "cls": cls, "mapped": mapped}


def collisions(opts, gold_i):
    """Question census: gold_empty (the gold normalises to ''), and the wrong options j that HELM's metrics confuse
    with the gold, each j in the first list that applies: identical, quasi_only, prefix_only."""
    g = opts[gold_i]
    out = {"gold_empty": normalize_text(g) == "", "identical": [], "quasi_only": [], "prefix_only": []}
    for j, o in enumerate(opts):
        if j == gold_i:
            continue
        if exact_match(g, o):
            out["identical"].append(j)
        elif quasi_exact_match(g, o):
            out["quasi_only"].append(j)
        elif quasi_prefix_exact_match(g, o):
            out["prefix_only"].append(j)
    return out


def any_collision(col):
    """A question collides when a wrong option is credited if chosen (gold_empty with no other non-empty option is
    already covered: then no list is non-empty)."""
    return bool(col["identical"] or col["quasi_only"] or col["prefix_only"])


# ----- Run names and perturbations -----

def run_field(run, key):
    """'a_okvqa:model=x,groups=y' -> value of `key` (None if absent)."""
    body = run.split(":", 1)[1] if ":" in run else run
    for part in body.split(","):
        if part.startswith(key + "="):
            return part[len(key) + 1:]
    return None


def group_of(run, family):
    return run_field(run, "groups") or family


def variant_of(pert):
    """'' for an original record; else the perturbation name, plus ':<language_code>' when it has one."""
    if not pert:
        return ""
    v = pert.get("name") or "?"
    if pert.get("language_code"):
        v += ":" + pert["language_code"]
    return v


def worst_name(perts):
    """Name of the stats.json entry (computed_on 'worst') that VHELM's leaderboard shows for a run whose instances
    carry these perturbation dicts: 'fairness' if any is a fairness perturbation, else 'robustness' if any is a
    robustness one, else the perturbation's own name (translation). None when the run has no perturbation."""
    perts = [p for p in perts if p]
    if not perts:
        return None
    if any(p.get("fairness") for p in perts):
        return "fairness"
    if any(p.get("robustness") for p in perts):
        return "robustness"
    return sorted(p.get("name") or "?" for p in perts)[0]


def stat_mean(stats, split, pert_name=None, computed_on=None):
    """Mean of the quasi_prefix_exact_match entry for this split: the unperturbed entry when pert_name is None, else
    the entry whose perturbation has this name and computed_on. None if absent."""
    for e in stats or []:
        n = e.get("name") or {}
        if n.get("name") != STAT or n.get("split") != split:
            continue
        p = n.get("perturbation")
        if pert_name is None:
            if not p:
                return e.get("mean")
        elif p and p.get("name") == pert_name and p.get("computed_on") == computed_on:
            return e.get("mean")
    return None


def qhash(iid, opts, gold_i):
    h = hashlib.sha1()
    h.update(str(iid).encode("utf-8"))
    for o in opts:
        h.update(b"\x00" + o.encode("utf-8"))
    h.update(b"\x01" + str(gold_i).encode("ascii"))
    return h.hexdigest()[:16]


def pert_key(pert):
    """'' for an original record, else the perturbation's name (prediction records may omit language_code)."""
    return (pert.get("name") or "?") if pert else ""


def instance_map(inst, split):
    """{(id, perturbation name): {'opts', 'gold', 'pert', 'variant'}} for main-split instances; gold None unless
    exactly one reference is tagged correct."""
    out = {}
    for it in inst or []:
        if not isinstance(it, dict) or it.get("split") != split:
            continue
        refs = it.get("references") or []
        opts = [((r.get("output") or {}).get("text") or "") for r in refs]
        correct = [k for k, r in enumerate(refs) if "correct" in (r.get("tags") or [])]
        pert = it.get("perturbation")
        out[(it.get("id"), pert_key(pert))] = {"opts": opts, "gold": correct[0] if len(correct) == 1 else None,
                                               "pert": pert, "variant": variant_of(pert)}
    return out


def new_sub():
    return {"n": 0, "h": 0, "i": 0, "unmapped": 0, "under": 0, "over": {c: 0 for c in OVER_CLASSES}}


def summarize_run(preds, imap):
    """Grade every first-trial record. Returns counts, per-variant subsets, the per-instance worst case over copies
    (when the run has perturbed copies), published-level flips, and the census of the questions graded."""
    c = {"n_pred": 0, "other_trial": 0, "no_instance": 0, "no_gold": 0, "duplicate": 0, "scored": 0,
         "map_checked": 0, "map_agree": 0}
    subsets, per_id, seen, questions, examples = {}, {}, set(), {}, []
    for p in preds or []:
        if not isinstance(p, dict):
            continue
        c["n_pred"] += 1
        if p.get("train_trial_index", 0) != 0:
            c["other_trial"] += 1
            continue
        key = (p.get("instance_id"), pert_key(p.get("perturbation")))
        q = imap.get(key)
        if q is None:
            c["no_instance"] += 1
            continue
        var = q["variant"]
        if q["gold"] is None:
            c["no_gold"] += 1
            continue
        if key in seen:
            c["duplicate"] += 1
            continue
        seen.add(key)
        r = grade(q["opts"], q["gold"], p.get("predicted_text"))
        c["scored"] += 1
        c["map_checked"] += 1
        mo = p.get("mapped_output")
        if (r["idx"] is None and mo is None) or (r["idx"] is not None and mo == r["mapped"]):
            c["map_agree"] += 1
        s = subsets.setdefault(var, new_sub())
        s["n"] += 1
        s["h"] += r["h"]
        s["i"] += r["i"]
        if r["idx"] is None:
            s["unmapped"] += 1
        if r["cls"] == "under":
            s["under"] += 1
        elif r["cls"]:
            s["over"][r["cls"][5:]] += 1
            if len(examples) < 3:
                examples.append((key[0], var, LETTERS[r["idx"]], LETTERS[q["gold"]], r["cls"][5:]))
        per_id.setdefault(key[0], []).append((var, r))
        qh = qhash(key[0], q["opts"], q["gold"])
        if (var, qh) not in questions:
            col = collisions(q["opts"], q["gold"])
            questions[(var, qh)] = {"iid": key[0], "k": len(q["opts"]), "gold_letter": LETTERS[q["gold"]],
                                    "col": {"gold_empty": col["gold_empty"],
                                            "identical": [LETTERS[j] for j in col["identical"]],
                                            "quasi_only": [LETTERS[j] for j in col["quasi_only"]],
                                            "prefix_only": [LETTERS[j] for j in col["prefix_only"]]},
                                    "texts": ({"gold": q["opts"][q["gold"]][:80],
                                               "others": {LETTERS[j]: q["opts"][j][:80]
                                                          for k2 in ("identical", "quasi_only", "prefix_only")
                                                          for j in col[k2]}}
                                              if (any_collision(col) or col["gold_empty"]) else None)}
    worst = None
    flips = []
    has_pert = any(v != "" for v in subsets)
    if has_pert:
        worst = new_sub()
        worst["ids_without_original"] = 0
        for iid, copies in per_id.items():
            if not any(v == "" for v, _r in copies):
                worst["ids_without_original"] += 1
                continue
            hw = min(r["h"] for _v, r in copies)
            iw = min(r["i"] for _v, r in copies)
            worst["n"] += 1
            worst["h"] += hw
            worst["i"] += iw
            if hw == 1 and iw == 0:
                v, r = sorted(((v, r) for v, r in copies if r["i"] == 0), key=lambda t: t[0])[0]
                cls = r["cls"][5:]
                worst["over"][cls] += 1
                flips.append({"id": iid, "variant": v, "letter": LETTERS[r["idx"]], "class": cls})
            elif hw == 0 and iw == 1:
                worst["under"] += 1
    else:
        for iid, copies in per_id.items():
            for v, r in copies:
                if r["cls"] and r["cls"] != "under":
                    flips.append({"id": iid, "variant": v, "letter": LETTERS[r["idx"]], "class": r["cls"][5:]})
    return {"counts": c, "subsets": subsets, "worst": worst, "flips": flips, "questions": questions,
            "examples": examples}


def published(summary):
    """The subset dict (n, h, i, unmapped, under, over by class) behind the published cell: the worst case when the
    run has perturbed copies, else the original records."""
    s = summary["worst"] if summary["worst"] is not None else summary["subsets"].get("", new_sub())
    return s


# ----- Ranks and rank agreement (as audits 91 and 92) -----

def min_ranks(acc):
    """acc {model: Fraction} -> {model: 1 + number of models with a strictly higher value}."""
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

THRESHOLDS = {"P1_share": Fraction(99, 100), "P2_min": 5, "P3_min": 10, "P3_ratio": 3, "P4_min": 1,
              "P5_pct": 1, "P6_places": 3, "P8_share": Fraction(1, 100), "P8_models": 3}


def verdicts(st, th=THRESHOLDS):
    """st: {'family_included': {fam: (included, listed)}, 'mmmu_gold_empty': int, 'tr_any': int, 'tr_q': int,
    'en_any': int, 'en_q': int, 'tr_identical': int, 'pub_over': int, 'pub_credits': int, 'movers': int,
    'zh_prefix': int, 'es_prefix': int, 'models_unmapped_base': int} -> {name: bool}."""
    p1 = all(n > 0 and Fraction(i, n) >= th["P1_share"] for i, n in st["family_included"].values())
    p3 = bool(st["tr_any"] >= th["P3_min"] and st["tr_any"] * st["en_q"] >= th["P3_ratio"] * st["en_any"] * st["tr_q"])
    return {
        "P1_reproduced": p1,
        "P2_mmmu_gold_empty": st["mmmu_gold_empty"] >= th["P2_min"],
        "P3_translation_collisions": p3,
        "P4_translation_identical": st["tr_identical"] >= th["P4_min"],
        "P5_overcredit_small": st["pub_credits"] > 0 and st["pub_over"] * 100 < th["P5_pct"] * st["pub_credits"],
        "P6_ranks_stable": st["movers"] == 0,
        "P7_chinese_prefix_more": st["zh_prefix"] > st["es_prefix"],
        "P8_format_loss": st["models_unmapped_base"] >= th["P8_models"],
    }


def verdict_word(v):
    return "HELD" if v else "FAILED"
