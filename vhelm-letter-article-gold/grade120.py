# SPDX-License-Identifier: Apache-2.0
"""Audit 120 grading helpers (standard library only).

HELM's quasi_prefix_exact_match normalises gold and answer with normalize_text, which lower-cases, removes ASCII
punctuation and removes the English articles a / an / the. A gold that is the option letter "A" (or "a", "(A)",
"A.") therefore normalises to the empty string, and every non-empty answer starts with the empty string, so every
non-empty answer is credited. normalize_text and quasi_prefix_exact_match below are transcribed from HELM
(src/helm/benchmark/metrics/evaluate_reference_metrics.py, Apache-2.0, Stanford CRFM).

The corrected "letter grade" keeps articles (HELM's own should_remove_articles=False switch, used since PR #3257 for
RealWorldQA only) and, for a one-word gold, compares the answer's first word with it.
Made with AI agents working in MV2's name (MV2 of Munim, Inc.). Apache-2.0.
"""
import re
import string
import zlib
from fractions import Fraction

STAT = "quasi_prefix_exact_match"
CLASSES = ("genuine", "free_article_gold", "prefix_word", "letter_only", "miss")
ANSWER_KINDS = ("latin_letter", "cyr_letter", "other", "empty")
LAT = "abcde"
CYR = "абвгд"  # Cyrillic a, be, ve, ge, de (Bulgarian option order)
FAMILIES = {"exams_v": "test", "mm_star": "valid", "blink": "valid"}


# ---- transcribed from HELM -------------------------------------------------------------------------------------
def normalize_text(text, should_remove_articles=True):
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


def quasi_prefix_exact_match(gold, pred):
    if not pred:
        return 0
    return 1 if normalize_text(pred).startswith(normalize_text(gold)) else 0


# ---- our grades and classes ------------------------------------------------------------------------------------
def first_word(pred):
    w = normalize_text(pred, should_remove_articles=False).split()
    return w[0] if w else ""


def letter_grade(gold, pred):
    """Articles kept; a one-word gold must equal the answer's first word, a longer gold must be a prefix."""
    g = normalize_text(gold, should_remove_articles=False)
    if not g or not pred:
        return 0
    p = normalize_text(pred, should_remove_articles=False)
    if len(g.split()) == 1:
        w = p.split()
        return 1 if w and w[0] == g else 0
    return 1 if p.startswith(g) else 0


def grade_record(golds, pred):
    """pred must already be stripped, as HELM strips completions before scoring."""
    q = max(quasi_prefix_exact_match(g, pred) for g in golds) if golds else 0
    lg = max(letter_grade(g, pred) for g in golds) if golds else 0
    art = any(normalize_text(g) == "" for g in golds)
    if q and lg:
        cls = "genuine"
    elif q:
        cls = "free_article_gold" if art else "prefix_word"
    elif lg:
        cls = "letter_only"
    else:
        cls = "miss"
    return {"qpem": q, "letter": lg, "cls": cls, "article_gold": art}


def is_cyrillic(text):
    return any("Ѐ" <= ch <= "ӿ" for ch in text)


def answer_kind(pred):
    f = first_word(pred)
    if not f:
        return "empty"
    if len(f) == 1 and f in LAT:
        return "latin_letter"
    if len(f) == 1 and f in CYR:
        return "cyr_letter"
    return "other"


def cyr_position_right(gold, pred):
    """A Latin letter answer that names the gold's option by position (a=1st, b=2nd, c=3rd, d=4th)."""
    g = normalize_text(gold, should_remove_articles=False)
    f = first_word(pred)
    if len(g) != 1 or g not in CYR or len(f) != 1 or f not in LAT:
        return False
    return LAT.index(f) == CYR.index(g)


def cyr_lookalike_b(gold, pred):
    """Latin 'B' for the Cyrillic third option 'V', which looks like B."""
    return normalize_text(gold, should_remove_articles=False) == "в" and first_word(pred) == "b"


def beyond_four(gold):
    g = normalize_text(gold, should_remove_articles=False)
    return g in ("e", "д") or (g != "" and g.isdigit())


# ---- run-level helpers -----------------------------------------------------------------------------------------
def run_field(run, key):
    body = run.split(":", 1)[1] if ":" in run else run
    for part in body.split(","):
        if part.startswith(key + "="):
            return part[len(key) + 1:]
    return None


def family_of(run):
    return run.split(":", 1)[0]


def instance_map(instances):
    out = {}
    for inst in instances:
        if inst.get("perturbation"):
            continue
        golds = [r["output"]["text"] for r in inst.get("references") or [] if "correct" in (r.get("tags") or [])]
        out[inst["id"]] = {"split": inst.get("split"), "golds": golds}
    return out


def stat_entry(stats, name, split):
    for s in stats or []:
        n = s.get("name") or {}
        if n.get("name") == name and n.get("split") == split and not n.get("perturbation"):
            return s
    return None


def new_counts():
    return {"kept": 0, "credit": 0, "letter": 0, "stored_missing": 0, "mismatch": 0, "article_gold": 0,
            "article_gold_nonempty_uncredited": 0, "beyond_four": 0, "cyr_gold": 0, "other_split": 0,
            "no_instance": 0, "skipped_perturbed": 0}


def new_cyr():
    return {"n": 0, "credit": 0, "latin_letter": 0, "cyr_letter": 0, "other": 0, "empty": 0, "pos_right": 0,
            "lookalike_b": 0, "latin_letter_credit": 0}


def summarize_run(preds, imap, split):
    c = new_counts()
    classes = {k: 0 for k in CLASSES}
    cyr = new_cyr()
    examples = {"free_article_gold": [], "prefix_word": [], "letter_only": []}
    for p in preds:
        if p.get("perturbation") or p.get("train_trial_index", 0) != 0:
            c["skipped_perturbed"] += 1
            continue
        info = imap.get(p.get("instance_id"))
        if info is None:
            c["no_instance"] += 1
            continue
        if info["split"] != split:
            c["other_split"] += 1
            continue
        c["kept"] += 1
        pred = (p.get("predicted_text") or "").strip()
        golds = info["golds"]
        r = grade_record(golds, pred)
        stored = (p.get("stats") or {}).get(STAT)
        if stored is None:
            c["stored_missing"] += 1
        elif float(stored) != float(r["qpem"]):
            c["mismatch"] += 1
        c["credit"] += r["qpem"]
        c["letter"] += r["letter"]
        classes[r["cls"]] += 1
        if r["article_gold"]:
            c["article_gold"] += 1
            if pred and stored is not None and float(stored) == 0.0:
                c["article_gold_nonempty_uncredited"] += 1
        if any(beyond_four(g) for g in golds):
            c["beyond_four"] += 1
        if r["cls"] in examples and len(examples[r["cls"]]) < 2:
            examples[r["cls"]].append((p.get("instance_id"), golds[0] if golds else None, pred[:40]))
        if golds and is_cyrillic(golds[0]):
            c["cyr_gold"] += 1
            cyr["n"] += 1
            cyr["credit"] += r["qpem"]
            k = answer_kind(pred)
            cyr[k] += 1
            if k == "latin_letter":
                cyr["latin_letter_credit"] += r["qpem"]
                if cyr_position_right(golds[0], pred):
                    cyr["pos_right"] += 1
                if cyr_lookalike_b(golds[0], pred):
                    cyr["lookalike_b"] += 1
    return {"counts": c, "classes": classes, "cyr": cyr, "examples": examples}


# ---- statistics ------------------------------------------------------------------------------------------------
def kendall_tau_b(x, y):
    nc = nd = tx = ty = 0
    n = len(x)
    for i in range(n):
        for j in range(i + 1, n):
            dx = (x[i] > x[j]) - (x[i] < x[j])
            dy = (y[i] > y[j]) - (y[i] < y[j])
            if dx == 0 and dy == 0:
                continue
            if dx == 0:
                tx += 1
            elif dy == 0:
                ty += 1
            elif dx == dy:
                nc += 1
            else:
                nd += 1
    den = ((nc + nd + tx) * (nc + nd + ty)) ** 0.5
    return None if den == 0 else (nc - nd) / den


def ranks_high(scores):
    return {m: 1 + sum(1 for o in scores.values() if o > s) for m, s in scores.items()}


def stable_hash(s):
    return zlib.crc32(s.encode("utf-8"))


# ---- pre-registered verdicts (frozen 2026-11-14) ---------------------------------------------------------------
def verdicts(st):
    """st: dict of pooled numbers; each verdict is True (HELD), False (FAILED) or None (not computable)."""
    v = {}
    fam = st["families"]
    ok = []
    for f in FAMILIES:
        x = fam.get(f) or {}
        ne = x.get("runs_nonempty", 0)
        ok.append(ne > 0 and Fraction(x.get("runs_included", 0), ne) >= Fraction(99, 100))
    v["P1"] = all(ok)
    p2 = []
    for f in ("mm_star", "blink"):
        x = fam.get(f) or {}
        p2.append(x.get("kept", 0) > 0 and Fraction(x.get("article_gold", 0), x["kept"]) >= Fraction(20, 100))
    v["P2"] = all(p2)
    cr = st["credits"]
    v["P3"] = None if cr == 0 else Fraction(st["free_article_gold"], cr) >= Fraction(5, 100)
    v["P4"] = st["models_drop_005"] >= 10
    taus = [t for t in st["taus"] if t is not None]
    v["P5"] = None if not taus else min(taus) < 0.90
    v["P6"] = None if cr == 0 else Fraction(st["prefix_word"], cr) < Fraction(5, 1000)
    letters = st["bg_latin_letter"] + st["bg_cyr_letter"]
    v["P7"] = None if letters == 0 else Fraction(st["bg_latin_letter"], letters) >= Fraction(60, 100)
    v["P8"] = None if st["bg_latin_letter"] == 0 else Fraction(st["bg_pos_right"], st["bg_latin_letter"]) >= \
        Fraction(35, 100)
    return v


def verdict_word(x):
    return "HELD" if x is True else ("FAILED" if x is False else "NOT COMPUTABLE")
