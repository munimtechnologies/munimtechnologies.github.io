"""How often does HELM Lite's GSM8K scorer grade an answer wrongly, in both directions? Core logic for audit 90.

HELM scores GSM8K with final_number_exact_match: the last number in the model's output must equal the last number of
the reference ("The answer is 18."), compared as strings. Its regex, -?[\\d,]+(?:.\\d+)?, lets a lone comma count as a
number and its unescaped '.' joins two numbers separated by any one character (HELM issue #4337, PRs #4317 and
#4341). Two further hazards are not in those reports: '$7.00' is not '7', and a model that keeps writing after its
answer (HELM runs many chat models with stop=none) is graded on whatever number it wrote last.

Four graders, applied to every archived prediction:
  H  HELM's scorer, transcribed (Apache-2.0, stanford-crfm/helm), gated against HELM's recorded score;
  F  the same with PR #4341's regex (-?\\d[\\d,]*(?:\\.\\d+)?), still a string comparison;
  N  F's last number compared with the key as a number (7.00 == 7);
  A  the stated answer: the number after the first 'answer is' (any case), else the last \\boxed{} number, else F's
     last number; compared as a number.
Standard library only. Apache-2.0. Authored by AI agents working in the name of MV2, Munim, Inc.
"""

import re
from fractions import Fraction

# ----- H: HELM's final_number_exact_match, transcribed (Apache-2.0, stanford-crfm/helm) -----

_HELM = re.compile(r"-?[\d,]+(?:.\d+)?")


def helm_final(x):
    matches = _HELM.findall(x or "")
    if not matches:
        return ""
    return matches[-1].replace(",", "")


def exact_match(gold, pred):
    if not pred:
        return 0
    return 1 if gold.strip() == pred.strip() else 0


def helm_fnem(gold, pred):
    return exact_match(helm_final(gold), helm_final(pred))


# ----- F: PR #4341's regex (a match starts with a digit; the decimal point is escaped) -----

_FIXED = re.compile(r"-?\d[\d,]*(?:\.\d+)?")


def fixed_final(x):
    matches = _FIXED.findall(x or "")
    if not matches:
        return ""
    return matches[-1].replace(",", "")


def fixed_fnem(gold, pred):
    return exact_match(fixed_final(gold), fixed_final(pred))


# ----- N and A: numeric comparison and the stated answer -----

_ANSWER = re.compile(r"answer is[\s:*$\\(\[{]*(?:boxed\{)?[\s$\\]*(-?\d[\d,]*(?:\.\d+)?)", re.I)
_BOXED = re.compile(r"boxed\{\s*\\?\$?\s*(-?\d[\d,]*(?:\.\d+)?)")


def to_num(s):
    """'1,500' -> 1500, '7.00' -> 7 (Fractions); None for '' or anything that is not one number."""
    s = (s or "").replace(",", "").strip()
    if not s:
        return None
    try:
        return Fraction(s)
    except (ValueError, ZeroDivisionError):
        return None


def num_eq(a, b):
    na, nb = to_num(a), to_num(b)
    return na is not None and nb is not None and na == nb


def stated(x):
    """(number string without commas, source): the number after the first 'answer is' that is followed by one
    ('phrase'); else the last \\boxed{} number ('boxed'); else F's last number ('last', '' if none)."""
    m = _ANSWER.search(x or "")
    if m:
        return m.group(1).replace(",", ""), "phrase"
    b = _BOXED.findall(x or "")
    if b:
        return b[-1].replace(",", ""), "boxed"
    return fixed_final(x), "last"


def grade(gold, pred):
    """All four grades of one prediction, plus what the class rules need."""
    key = fixed_final(gold)
    s, src = stated(pred)
    return {
        "h": helm_fnem(gold, pred),
        "f": fixed_fnem(gold, pred),
        "n": 1 if num_eq(key, fixed_final(pred)) else 0,
        "a": 1 if num_eq(key, s) else 0,
        "key": key,
        "helm_final": helm_final(pred),
        "fixed_final": fixed_final(pred),
        "stated": s,
        "source": src,
    }


UP_CLASSES = ("comma_only", "dot_merge", "decimal_format", "run_on", "other")
DOWN_CLASSES = ("helm_regex_only", "stated_differs", "other")


def flip_class(g):
    """Why the stated-answer grade A differs from HELM's grade H (None when they agree). Up-flips (H 0, A 1), first
    rule that applies: HELM's last match was a lone comma; HELM's final number joined two numbers across a character
    that is not a decimal point; the last number equals the key as a number but not as a string; the stated answer
    equals the key but the last number does not. Down-flips (H 1, A 0): F's last number does not equal the key (HELM's
    credit comes only from its own regex); the last number equals the key but the stated answer does not."""
    if g["h"] == g["a"]:
        return None
    if g["a"] == 1:
        hf = g["helm_final"]
        if hf == "":
            return "comma_only"
        if any(c not in "0123456789.-" for c in hf):
            return "dot_merge"
        if num_eq(g["key"], g["fixed_final"]):
            return "decimal_format"
        if g["source"] in ("phrase", "boxed"):
            return "run_on"
        return "other"
    if not num_eq(g["key"], g["fixed_final"]):
        return "helm_regex_only"
    if g["source"] in ("phrase", "boxed"):
        return "stated_differs"
    return "other"


# ----- Ranks and rank agreement -----

def min_ranks(acc):
    """acc {model: Fraction} -> {model: 1 + number of models with a strictly higher accuracy}."""
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


# ----- Pre-registered verdicts P2-P6 (P1 is decided in job.py; P7 is graded by reading, next run) -----

def predictions90(net, decimal_only, gain_stop, gain_other, moved, up, down, th):
    """net: A-correct minus H-correct over all included predictions; decimal_only: predictions with H 0, F 0, N 1;
    gain_stop, gain_other: (sum of per-run accuracy gains A - H as a Fraction, number of runs) for stop=none runs
    and the rest; moved: models whose rank moves by at least th['P5_min_move'] places; up, down: flip counts."""
    def mean(t):
        return Fraction(t[0]) / t[1]
    return {
        "P2_net_rescues": net >= th["P2_min_net"],
        "P3_decimal_rescues": decimal_only >= th["P3_min_decimal"],
        "P4_stop_none_gains_more": bool(gain_stop[1] >= th["P4_min_group"] and gain_other[1] >= th["P4_min_group"]
                                        and mean(gain_stop) > mean(gain_other)),
        "P5_rank_moves": moved >= th["P5_min_models"],
        "P6_down_flips_rare": bool(up > 0 and th["P6_ratio"] * down <= up),
    }


# ----- HELM Lite run selection (copied unchanged from audit 86, gsm86.py) -----

def _version(s):
    out = []
    for p in (s or "").lstrip("v").split("."):
        try:
            out.append(int(p))
        except ValueError:
            out.append(-1)
    return tuple(out)


def run_model(run):
    """'gsm:model=x_y,stop=none' -> 'x_y' (None if no model= part)."""
    body = run.split(":", 1)[1] if ":" in run else run
    for part in body.split(","):
        if part.startswith("model="):
            return part[len("model="):]
    return None


def select_runs(run_suites, prefix="gsm:"):
    """One run per model among keys starting with `prefix`: the newest suite, then the shortest and alphabetically
    first key. Returns ({model: (run, suite)}, number of runs dropped as duplicates)."""
    best, dropped = {}, 0
    for run, suite in run_suites.items():
        if not run.startswith(prefix):
            continue
        m = run_model(run)
        if m is None:
            continue
        cand = (run, suite)
        if m in best:
            dropped += 1
            cur = best[m]
            if (_version(suite), -len(run), [-ord(c) for c in run]) > (_version(cur[1]), -len(cur[0]),
                                                                           [-ord(c) for c in cur[0]]):
                best[m] = cand
        else:
            best[m] = cand
    return best, dropped


def is_stop_none(run):
    return "stop=none" in run.split(":", 1)[-1].split(",")
