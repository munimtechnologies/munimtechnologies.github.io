"""Does HELM issue #4358 (multiple-choice option collisions) reach HELM Lite's published scores? Core logic, audit 92.

HELM's multiple_choice_joint adapter maps the model's answer letter to the TEXT of that option
(output_mapping = {letter: reference text}), and the reference metrics then compare that text with the gold
option's text. Two consequences follow from the code itself:
  * a wrong letter gets full credit when its option text matches the gold's: string-identical options under
    exact_match (HELM Lite's main metric for MMLU and OpenBookQA), and options that differ only in case,
    ASCII punctuation, articles or spacing under quasi_exact_match (HELM Lite's main metric for MedQA): '-7' vs '7',
    '1.25' vs '125'. quasi_prefix_exact_match (not a main metric in HELM Lite) also credits a wrong option whose
    normalised text merely starts with the gold's ('2' vs '24');
  * an output that is not exactly one of the option letters after strip() maps to None and scores 0 (HELM Lite asks
    for 1 output token, so the archive cannot say which option was meant).

Graders applied to every archived first-trial prediction:
  H  HELM's score: letter -> option text -> the benchmark's main metric against the gold option text (transcribed
     from stanford-crfm/helm, Apache-2.0), gated against HELM's recorded score;
  I  option identity: 1 when the letter names the gold option itself, else 0.
Standard library only. Apache-2.0. Authored by AI agents working in the name of MV2, Munim, Inc.
"""

import re
import string

LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"

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


METRICS = {"exact_match": exact_match, "quasi_exact_match": quasi_exact_match}


# ----- The letter mapping (MultipleChoiceJointAdapter: 'A', 'B', ... in reference order; pred.strip()) -----

def letter_index(pred, k):
    """Index of the option HELM's output_mapping gives for this output, or None when the stripped output is not
    exactly one of the first k capital letters."""
    s = (pred or "").strip()
    if len(s) == 1 and s in LETTERS[:k]:
        return LETTERS.index(s)
    return None


def unmapped_kind(pred, k):
    """Why an output maps to no option: 'empty', 'lowercase_letter' (a valid letter in lower case),
    'letter_out_of_range' (a capital letter beyond the k options), or 'other'."""
    s = (pred or "").strip()
    if not s:
        return "empty"
    if len(s) == 1 and s.upper() in LETTERS[:k] and s != s.upper():
        return "lowercase_letter"
    if len(s) == 1 and s in LETTERS:
        return "letter_out_of_range"
    return "other"


def grade(opts, gold_i, pred, metric):
    """H (HELM's score) and I (option identity) for one prediction, with the flip class:
    'identical' (H 1, I 0, the chosen option's text is string-identical to the gold's), 'quasi_only' (H 1, I 0,
    equal only after HELM's normalisation), 'under' (H 0, I 1: the gold letter scored 0, e.g. an empty option text).
    """
    k = len(opts)
    idx = letter_index(pred, k)
    if idx is None:
        return {"idx": None, "h": 0, "i": 0, "cls": None, "unmapped": unmapped_kind(pred, k), "mapped": None}
    mapped = opts[idx]
    gold = opts[gold_i]
    h = METRICS[metric](gold, mapped)
    i = 1 if idx == gold_i else 0
    cls = None
    if h == 1 and i == 0:
        cls = "identical" if exact_match(gold, mapped) == 1 else "quasi_only"
    elif h == 0 and i == 1:
        cls = "under"
    return {"idx": idx, "h": h, "i": i, "cls": cls, "unmapped": None, "mapped": mapped}


# ----- Question-level census: which wrong options can a metric not tell from the gold? -----

def collisions(opts, gold_i):
    """Wrong options j (indices) whose text HELM's metrics confuse with the gold's, each j in the first list that
    applies: 'identical' (exact_match 1), 'quasi_only' (quasi_exact_match 1), 'prefix_only'
    (quasi_prefix_exact_match 1)."""
    g = opts[gold_i]
    out = {"identical": [], "quasi_only": [], "prefix_only": []}
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


def gold_norm_empty(opts, gold_i):
    """True when HELM's normalisation turns the gold option into '' (every non-empty option then prefix-matches)."""
    return normalize_text(opts[gold_i]) == ""


# ----- Ranks and rank agreement (copied unchanged from audit 91, grade91.py) -----

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


# ----- HELM Lite run selection: one run per (model, subject) of one benchmark -----

def _version(s):
    out = []
    for p in (s or "").lstrip("v").split("."):
        try:
            out.append(int(p))
        except ValueError:
            out.append(-1)
    return tuple(out)


def run_part(run, key):
    """'mmlu:subject=x,method=y,model=a_b' -> value of `key` (None if absent)."""
    body = run.split(":", 1)[1] if ":" in run else run
    for part in body.split(","):
        if part.startswith(key + "="):
            return part[len(key) + 1:]
    return None


def select_runs(run_suites, prefix, must_contain=None):
    """One run per (model, subject) among keys starting with `prefix` (and containing `must_contain`, if given);
    subject '-' when the run has none. The newest suite wins, then the shortest and alphabetically first key
    (audit 86's rule). Returns ({(model, subject): (run, suite)}, runs dropped as duplicates)."""
    best, dropped = {}, 0
    for run, suite in run_suites.items():
        if not run.startswith(prefix):
            continue
        if must_contain is not None and must_contain not in run:
            continue
        m = run_part(run, "model")
        if m is None:
            continue
        s = run_part(run, "subject") or "-"
        k, cand = (m, s), (run, suite)
        if k in best:
            dropped += 1
            cur = best[k]
            if (_version(suite), -len(run), [-ord(c) for c in run]) > (_version(cur[1]), -len(cur[0]),
                                                                           [-ord(c) for c in cur[0]]):
                best[k] = cand
        else:
            best[k] = cand
    return best, dropped


# ----- Pre-registered verdicts P2-P7 (P1 is decided in job.py) -----

def predictions92(q_quasi_medqa, over_medqa, n_medqa, moved_medqa, q_prefix_all, q_quasi_all, q_identical_all,
                  models_unmapped_medqa, th):
    """q_quasi_medqa: MedQA questions whose gold has a quasi_only collision; over_medqa / n_medqa: MedQA predictions
    with H 1 and I 0 / all included MedQA predictions; moved_medqa: models whose MedQA rank moves by at least
    th['P4_min_move'] places between H and I; q_prefix_all, q_quasi_all, q_identical_all: questions (all three
    benchmarks) with a prefix_only / quasi_only / identical collision; models_unmapped_medqa: models with at least
    th['P7_share'] of their MedQA predictions unmapped."""
    return {
        "P2_quasi_collision_medqa": q_quasi_medqa >= th["P2_min_questions"],
        "P3_overcredit_small_medqa": bool(n_medqa > 0 and over_medqa * th["P3_den"] <= n_medqa * th["P3_num"]),
        "P4_medqa_ranks_stable": moved_medqa == 0,
        "P5_prefix_hazard_larger": bool(q_prefix_all >= th["P5_min_prefix"]
                                        and q_prefix_all >= th["P5_ratio"] * q_quasi_all),
        "P6_identical_duplicates": q_identical_all >= th["P6_min_identical"],
        "P7_format_loss_medqa": models_unmapped_medqa >= th["P7_min_models"],
    }
