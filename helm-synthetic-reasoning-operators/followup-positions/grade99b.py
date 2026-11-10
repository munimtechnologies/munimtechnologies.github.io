"""Audit 99 follow-up (post-hoc, descriptive): of HELM Classic's synthetic-reasoning credits that audit 99's
operator-aware grade kept, how many still put the operators in the wrong places?

Audit 99's operator-aware grade (OA) asks for HELM's quasi-exact match AND the gold's sequence of + - * =
characters. It does not ask where the operators sit, so "Rule: + X + Y" still matches the gold "Rule: + X Y +". This
module adds a pattern-exact grade (PX): quasi-exact match AND the same sequence of tokens, where a token is a run of
letters or digits or one operator character, after lower-casing and dropping the articles a/an/the (which HELM's
quasi-exact match also drops). Other punctuation (":", ".", ",") and spacing are ignored.

Every quasi-exact credit falls in exactly one class:
  exact          HELM's exact_match is 1
  format_only    PX is 1 but exact is 0 (case, spacing, other punctuation, articles)
  ops_misplaced  OA is 1 but PX is 0 (the gold's operators in the gold's order, in other places)
  ops_blind      OA is 0 (audit 99's operator-blind credits)
EM implies PX and PX implies OA (for every gold), so the classes do not overlap. Apache-2.0.
"""

import re

import grade99 as g

ARTICLES = frozenset(("a", "an", "the"))
TOKEN = re.compile(r"[a-z0-9]+|[+\-*=]")
CLASSES = ("exact", "format_only", "ops_misplaced", "ops_blind")


def tokens(text):
    """Lower-cased word/digit runs and single operator characters, in order, without articles."""
    return [t for t in TOKEN.findall((text or "").lower()) if t not in ARTICLES]


def pattern_exact(gold, pred):
    """1 when HELM's quasi-exact match holds AND the token sequences are equal."""
    return 1 if g.quasi_exact_match(gold, pred) and tokens(gold) == tokens(pred) else 0


def grade_record_b(golds, pred_text):
    """Audit 99's grades plus PX (a max over golds) and the record's class (None when quasi-exact is 0)."""
    base = g.grade_record(golds, pred_text)
    pred = (pred_text or "").strip()
    px = max((pattern_exact(gl, pred) for gl in golds), default=0)
    if base["qem"] == 0:
        cls = None
    elif base["em"] == 1:
        cls = "exact"
    elif px == 1:
        cls = "format_only"
    elif base["oa"] == 1:
        cls = "ops_misplaced"
    else:
        cls = "ops_blind"
    return {"em": base["em"], "qem": base["qem"], "oa": base["oa"], "px": px, "cls": cls}


def summarize_run_b(instances, preds):
    """Like grade99.summarize_run (same record selection, same stored-score check), with PX and the four classes.

    trials: {trial: {n, em, qem, oa, px}}; classes: {class: count}; keys: {class: [(instance id, trial)]} for the
    three non-exact classes.
    """
    gold = {}
    for inst in instances or []:
        if isinstance(inst, dict) and inst.get("split") == "test":
            gold[inst.get("id")] = [((r.get("output") or {}).get("text") or "")
                                    for r in inst.get("references") or []
                                    if isinstance(r, dict) and "correct" in (r.get("tags") or [])]
    counts = {"n_records": 0, "perturbed": 0, "not_test": 0, "duplicate": 0, "kept": 0}
    trials, seen = {}, set()
    classes = {c: 0 for c in CLASSES}
    keys = {c: [] for c in CLASSES if c != "exact"}
    stat_missing = stat_mismatch = 0
    for r in preds or []:
        if not isinstance(r, dict):
            continue
        counts["n_records"] += 1
        if r.get("perturbation") is not None:
            counts["perturbed"] += 1
            continue
        iid, t = r.get("instance_id"), r.get("train_trial_index", 0)
        if iid not in gold:
            counts["not_test"] += 1
            continue
        if (iid, t) in seen:
            counts["duplicate"] += 1
            continue
        seen.add((iid, t))
        counts["kept"] += 1
        gr = grade_record_b(gold[iid], r.get("predicted_text"))
        acc = trials.setdefault(t, {"n": 0, "em": 0, "qem": 0, "oa": 0, "px": 0})
        acc["n"] += 1
        for k in ("em", "qem", "oa", "px"):
            acc[k] += gr[k]
        stored = (r.get("stats") or {}).get(g.STAT_QEM)
        if not g.is_number(stored):
            stat_missing += 1
        elif int(round(stored)) != gr["qem"]:
            stat_mismatch += 1
        if gr["cls"] is not None:
            classes[gr["cls"]] += 1
            if gr["cls"] != "exact":
                keys[gr["cls"]].append((iid, t))
    return {"counts": counts, "trials": trials, "classes": classes, "keys": keys,
            "stat_missing": stat_missing, "stat_mismatch": stat_mismatch}


def v1_totals(classes, trials_list):
    """Audit 99's totals rebuilt from the four classes (used to check this job reproduces audit 99 exactly)."""
    em = sum(v["em"] for tr in trials_list for v in tr.values())
    qem = sum(v["qem"] for tr in trials_list for v in tr.values())
    oa = sum(v["oa"] for tr in trials_list for v in tr.values())
    return {"em": em, "qem": qem, "oa": oa, "blind": classes["ops_blind"],
            "other_norm": classes["format_only"] + classes["ops_misplaced"]}


def stable_hash(salt):
    """A small hash that is the same in every process (Python's hash() of a str is not)."""
    h = 0
    for ch in salt:
        h = (h * 131 + ord(ch)) % 1000003
    return h


def pick(lst, salt):
    """One element of lst chosen by a stable hash of salt (None when lst is empty)."""
    if not lst:
        return None
    return lst[stable_hash(salt) % len(lst)]
