# Exposure of real MATH gold answers to the math-equiv hazards.
#
# Measures M0-M6 exactly as pre-registered in prereg.md, using the published
# math_equiv.py (a faithful transcription of the Hendrycks MATH strip_string /
# is_equiv used by lm-evaluation-harness and verl). Standard library only.
#
# Apache-2.0. Made with AI by MV2 of Munim, Inc.

import re

import math_equiv as me

TEXT_SPACE = "\\text{ "
CONNECTIVE = re.compile(r"\b(or|and)\b")
INT_FRAC = re.compile(r"^(-?)\\[dt]?frac\{(\d+)\}\{(\d+)\}$")
VARIANTS = (("L", False), ("C", True))  # L = lm-evaluation-harness, C = original/verl


def extract_gold(solution):
    """lm-evaluation-harness gold: remove_boxed(last_boxed_only_string(solution)), or None."""
    boxed = me.last_boxed_only_string(solution)
    if boxed is None:
        return None
    try:
        return me.remove_boxed(boxed)
    except AssertionError:
        return None


def strip_error(gold, catch_all):
    """Name of the exception strip_string raises on gold, or None if it normalizes."""
    try:
        me.strip_string(gold, catch_all=catch_all)
    except Exception as e:
        return type(e).__name__
    return None


def before_units(gold):
    """gold after the strip_string steps that run before remove_right_units."""
    s = gold.replace("\n", "").replace("\\!", "").replace("\\\\", "\\")
    s = s.replace("tfrac", "frac").replace("dfrac", "frac")
    s = s.replace("\\left", "").replace("\\right", "")
    s = s.replace("^{\\circ}", "").replace("^\\circ", "").replace("\\$", "")
    return s


def text_units(gold):
    """Group A: (number of '\\text{ ' occurrences, discarded tail or None)."""
    s = before_units(gold)
    n = s.count(TEXT_SPACE)
    tail = s.split(TEXT_SPACE, 1)[1] if n == 1 else None
    return n, tail


def slash_rewrite(gold):
    """Group C: '[-]a/b' for an integer-fraction gold, else None. Returns (rewrite, negative)."""
    m = INT_FRAC.match(gold.strip())
    if not m:
        return None, None
    sign, a, b = m.groups()
    return sign + a + "/" + b, sign == "-"


def measure(golds):
    """golds: list of (unique_id, gold string). Returns the M0-M6 counts and listings."""
    n = len(golds)
    r = {"n_gold": n}
    r["M0"] = {k: sum(me.is_equiv(g, g, catch_all=c) for _, g in golds) for k, c in VARIANTS}

    m1 = {}
    for k, c in VARIANTS:
        by_type, ids = {}, []
        for uid, g in golds:
            err = strip_error(g, c)
            if err:
                by_type[err] = by_type.get(err, 0) + 1
                ids.append(uid)
        m1[k] = {"count": len(ids), "by_type": by_type, "ids": ids}
    r["M1"] = m1
    c_ids = set(m1["C"]["ids"])
    gold_of = dict(golds)
    r["M1_L_only"] = [{"id": uid, "gold": gold_of[uid]} for uid in m1["L"]["ids"]
                      if uid not in c_ids]

    items = []
    for uid, g in golds:
        cnt, tail = text_units(g)
        if cnt:
            items.append({"id": uid, "gold": g, "n": cnt, "tail": tail,
                          "connective": bool(tail and CONNECTIVE.search(tail))})
    r["M2"] = {"count": len(items),
               "M2a": sum(1 for i in items if i["n"] == 1),
               "M2b": sum(1 for i in items if i["connective"]),
               "M2c": sum(1 for i in items if i["n"] >= 2),
               "items": items}

    for key, make in (("M3", lambda g: " " + g), ("M4", lambda g: g + " ")):
        out = {}
        for k, c in VARIANTS:
            bad = [uid for uid, g in golds if not me.is_equiv(make(g), g, catch_all=c)]
            out[k] = {"count": len(bad), "ids": bad}
        r[key] = out
    r["M3"]["items"] = [{"id": uid, "gold": gold_of[uid]} for uid in r["M3"]["L"]["ids"]]

    exposed = [(uid, g) for uid, g in golds if "\\frac" in g]
    m5 = {"exposed": len(exposed)}
    for k, c in VARIANTS:
        m5[k] = sum(1 for _, g in exposed
                    if not me.is_equiv(g.replace("\\frac", "\\dfrac"), g, catch_all=c))
    r["M5"] = m5

    m6 = {"pos": {"n": 0, "L": 0, "C": 0}, "neg": {"n": 0, "L": 0, "C": 0}, "neg_ids": []}
    for uid, g in golds:
        rw, neg = slash_rewrite(g)
        if rw is None:
            continue
        side = m6["neg" if neg else "pos"]
        side["n"] += 1
        for k, c in VARIANTS:
            side[k] += bool(me.is_equiv(rw, g, catch_all=c))
        if neg:
            m6["neg_ids"].append(uid)
    r["M6"] = m6
    return r


def grade(r):
    """Grade the pre-registered predictions P1-P6 against measure() output."""
    n = r["n_gold"]
    pct = lambda x: 100.0 * x / n if n else 0.0
    pos, neg = r["M6"]["pos"], r["M6"]["neg"]
    pos_ok = all(pos[k] >= 0.99 * pos["n"] for k in ("L", "C")) and pos["n"] > 0
    neg_ok = all(neg[k] == 0 for k in ("L", "C")) and neg["n"] >= 50
    m3 = pct(r["M3"]["L"]["count"])
    return {
        "P1": {"hit": pct(r["M2"]["count"]) <= 3.0, "value_pct": pct(r["M2"]["count"])},
        "P2": {"hit": r["M2"]["M2b"] >= 1, "value": r["M2"]["M2b"]},
        "P3": {"hit": pct(r["M1"]["L"]["count"]) <= 1.0
                      and r["M1"]["L"]["count"] >= r["M1"]["C"]["count"],
               "L_pct": pct(r["M1"]["L"]["count"]), "C_pct": pct(r["M1"]["C"]["count"])},
        "P4": {"hit": pos_ok and neg_ok, "pos": pos, "neg": neg},
        "P5": {"hit": 0.1 <= m3 <= 3.0, "value_pct": m3},
        "P6": {"hit": r["M0"]["L"] == n and r["M0"]["C"] == n, "value": r["M0"]},
    }
