"""Does model consensus find GSM8K's flawed questions? Core logic for audit 86.

Audits 77-85 scored a model-consensus flag for wrong answer keys on MMLU and MMLU-Pro against MMLU-Redux's expert
labels, which cover a random sample. This audit moves to a free-response benchmark with complete labels: GSM8K's
1,319 test questions, every one of which GSM8K-Platinum (Vendrow et al., arXiv 2502.03461) marks as kept by model
consensus, verified, revised (wrong answer key) or removed (rejected, mostly ambiguous). Model answers come from
Stanford CRFM's HELM Lite per-question outputs (about 90 models, 5-shot chain of thought).

HELM's own scorer is transcribed below (get_final_number / exact_match from HELM's
evaluate_reference_metrics.final_number_exact_match, Apache-2.0, including its unescaped '.' in the regex) and gated
against HELM's recorded score for every prediction. The AUC and equal-budget counts are copied unchanged from audit
84 (panel84.py, from audit 83). Standard library only. Apache-2.0. Authored by AI agents working in the name of MV2,
Munim, Inc.
"""

import re
from fractions import Fraction

ERR = ("rejected", "revised")
CLEAN = ("verified", "consensus")
REVIEWED = ("rejected", "revised", "verified")

# ----- HELM's final_number_exact_match, transcribed (Apache-2.0, stanford-crfm/helm) -----

_FINAL_NUMBER = re.compile(r"-?[\d,]+(?:.\d+)?")


def get_final_number(x):
    matches = _FINAL_NUMBER.findall(x or "")
    if not matches:
        return ""
    return matches[-1].replace(",", "")


def exact_match(gold, pred):
    if not pred:
        return 0
    return 1 if gold.strip() == pred.strip() else 0


def final_number_exact_match(gold, pred):
    return exact_match(get_final_number(gold), get_final_number(pred))


# ----- GSM8K and GSM8K-Platinum -----

def norm_q(s):
    """Whitespace-normalised question text (the join key)."""
    return " ".join((s or "").split())


def gsm_final(answer):
    """GSM8K's final answer: the text after '####', stripped, commas removed ('' if absent)."""
    a = answer or ""
    if "####" not in a:
        return ""
    return a.split("####")[-1].strip().replace(",", "")


def text_index(texts):
    """texts: list of question strings. Returns ({norm text: position} for texts that occur once, set of norm texts
    that occur more than once)."""
    seen, dup = {}, set()
    for i, t in enumerate(texts):
        k = norm_q(t)
        if k in seen:
            dup.add(k)
        else:
            seen[k] = i
    return {k: i for k, i in seen.items() if k not in dup}, dup


def platinum_labels(gsm_rows, plat_rows):
    """gsm_rows: [(question, answer)] for GSM8K test in order; plat_rows: [(question, answer, cleaning_status)].
    A GSM8K row whose question occurs once in GSM8K gets the status of the Platinum row with the same normalised
    question, or 'rejected' if no Platinum row has it (Platinum removed it); a GSM8K question that occurs more than
    once is labelled 'duplicate' and left out. Returns (labels {position: label}, plat_answer {position: Platinum's
    final answer}, counts)."""
    uniq, dup = text_index([q for q, _a in gsm_rows])
    labels, plat_answer = {}, {}
    counts = {"gsm_rows": len(gsm_rows), "plat_rows": len(plat_rows), "matched": 0, "to_duplicate": 0,
              "unmatched": 0, "matched_twice": 0}
    for q, a, status in plat_rows:
        k = norm_q(q)
        if k in dup:
            counts["to_duplicate"] += 1
            continue
        i = uniq.get(k)
        if i is None:
            counts["unmatched"] += 1
            continue
        if i in labels:
            counts["matched_twice"] += 1
            continue
        labels[i] = status
        plat_answer[i] = gsm_final(a)
        counts["matched"] += 1
    for i, (q, _a) in enumerate(gsm_rows):
        if norm_q(q) in dup:
            labels[i] = "duplicate"
        elif i not in labels:
            labels[i] = "rejected"
    tally = {}
    for v in labels.values():
        tally[v] = tally.get(v, 0) + 1
    counts["labels"] = dict(sorted(tally.items()))
    return labels, plat_answer, counts


# ----- HELM runs -----

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


# ----- Votes, flags, scores -----

def vote_counts(answers, key):
    """answers: list of final-number strings ('' or None = no answer). Returns ({answer: votes} over non-empty
    answers, key votes, no-answer count)."""
    counts, none = {}, 0
    for a in answers:
        if not a:
            none += 1
            continue
        counts[a] = counts.get(a, 0) + 1
    return counts, counts.get(key, 0), none


def consensus(counts, key):
    """The single most-voted non-key answer and its votes; (None, top) when no non-key answer or a tie at the top."""
    best, top, tied = None, 0, False
    for a in sorted(counts):
        if a == key:
            continue
        n = counts[a]
        if n > top:
            best, top, tied = a, n, False
        elif n == top and n > 0:
            tied = True
    if best is None or tied:
        return None, top
    return best, top


def flag_question(counts, key, min_agree):
    ci, n = consensus(counts, key)
    return ci is not None and n >= min_agree and n > counts.get(key, 0), ci, n


def margin(counts, key):
    """Votes for the most-voted non-key answer minus votes for the key."""
    other = max([n for a, n in counts.items() if a != key] or [0])
    return other - counts.get(key, 0)


def panel_view(panel, answers_by_model, keys):
    """For every question q in keys: (counts, key votes, no-answer count, size of panel with a record on q).
    answers_by_model: {model: {q: answer string}} (a missing q = no record)."""
    out = {}
    for q, key in keys.items():
        ans = [answers_by_model.get(m, {}).get(q) for m in panel]
        counts, kv, none = vote_counts(ans, key)
        covered = sum(1 for m in panel if q in answers_by_model.get(m, {}))
        out[q] = (counts, kv, none, covered)
    return out


def flags_from_view(view, keys, panel_size, min_agree):
    """Four flags per question from one panel's view: consensus (>= min_agree on one non-key answer, more than the
    key), unanimous (all panel_size on one non-key answer), any_wrong (fewer than panel_size give the key: the
    Platinum-style filter), and the margin score."""
    cons, unan, anyw, score = {}, {}, {}, {}
    for q, key in keys.items():
        counts, kv, _none, _cov = view[q]
        cons[q] = flag_question(counts, key, min_agree)[0]
        unan[q] = flag_question(counts, key, panel_size)[0]
        anyw[q] = kv < panel_size
        score[q] = margin(counts, key)
    return cons, unan, anyw, score


def no_key_flags(view, min_cov):
    """No model with a record gives the key, and at least min_cov models have a record."""
    return {q: (v[3] >= min_cov and v[1] == 0) for q, v in view.items()}


def precision(flags, labels, kinds_err=ERR, kinds_all=ERR + CLEAN):
    """(error-labelled flagged, labelled flagged) over questions whose label is in kinds_all."""
    e = j = 0
    for q, f in flags.items():
        if not f:
            continue
        lab = labels.get(q)
        if lab in kinds_all:
            j += 1
            if lab in kinds_err:
                e += 1
    return e, j


def recall(flags, labels):
    """(error-labelled flagged, error-labelled)."""
    err = [q for q in flags if labels.get(q) in ERR]
    return sum(1 for q in err if flags[q]), len(err)


# ----- AUC and equal-budget counts (copied unchanged from audit 84) -----

def auc(pos, neg):
    """Probability that a positive scores above a negative, ties counting one half (Mann-Whitney), as a Fraction;
    None if either list is empty. Doubled average ranks keep the arithmetic exact."""
    if not pos or not neg:
        return None
    allv = sorted([(v, 1) for v in pos] + [(v, 0) for v in neg], key=lambda t: t[0])
    n = len(allv)
    rank2_pos, i = 0, 0
    while i < n:
        j = i
        while j + 1 < n and allv[j + 1][0] == allv[i][0]:
            j += 1
        r2 = (i + 1) + (j + 1)
        rank2_pos += r2 * sum(1 for t in allv[i:j + 1] if t[1] == 1)
        i = j + 1
    n_pos, n_neg = len(pos), len(neg)
    return Fraction(rank2_pos - n_pos * (n_pos + 1), 2 * n_pos * n_neg)


def budget_counts(score, sets, budget):
    """Expected counts when the `budget` highest-scoring questions are sent to review and ties at the cut are broken
    uniformly at random: whole score levels are taken from the top; the level that straddles the cut contributes the
    fraction (budget - taken) / level size of its members. Returns one Fraction per set in `sets` (each a set of
    question ids): the expected number of reviewed questions from that set."""
    levels = {}
    for q, v in score.items():
        levels.setdefault(v, []).append(q)
    out = [Fraction(0)] * len(sets)
    taken = 0
    for v in sorted(levels, reverse=True):
        if taken >= budget:
            break
        qs = levels[v]
        f = Fraction(1) if taken + len(qs) <= budget else Fraction(budget - taken, len(qs))
        for i, s in enumerate(sets):
            out[i] += f * sum(1 for q in qs if q in s)
        taken = min(budget, taken + len(qs))
    return out


def ranked_models(acc):
    """Models by accuracy (correct / n, descending), ties by name. acc: {model: (correct, n)}."""
    return sorted(acc, key=lambda m: (-(Fraction(acc[m][0], acc[m][1]) if acc[m][1] else Fraction(0)), m))


def budget_precision(score, labels, budget):
    """(expected error-labelled, expected labelled) among the `budget` highest-scoring questions."""
    err = {q for q in score if labels.get(q) in ERR}
    lab = {q for q in score if labels.get(q) in ERR + CLEAN}
    e, j = budget_counts(score, [err, lab], budget)
    return e, j


# ----- Pre-registered verdicts P2-P7 (P1 is decided in job.py) -----

def _gt(a, b):
    """a, b: (num, den) pairs; a/b comparison as Fractions, False if a denominator is 0."""
    return bool(a[1] and b[1] and Fraction(a[0], a[1]) > Fraction(b[0], b[1]))


def predictions86(cons, anyw, auc_s1, rec, nokey, n_nokey, b_s1, b_s5, th):
    """cons, anyw, nokey: (error-labelled, labelled) of S1's consensus flag, S1's any-wrong flag and the no-key
    flag; auc_s1: S1 margin AUC (Fraction or None); rec: (flagged errors, errors) of S1's consensus flag; n_nokey:
    labelled no-key questions; b_s1, b_s5: equal-budget (expected error-labelled, expected labelled) of S1 and S5."""
    return {
        "P2_consensus_precision": bool(cons[1] and Fraction(cons[0], cons[1]) >= th["P2_min_precision"]),
        "P3_consensus_beats_any_wrong": _gt(cons, anyw),
        "P4_margin_auc": bool(auc_s1 is not None and auc_s1 >= th["P4_min_auc"]),
        "P5_recall": bool(rec[1] and Fraction(rec[0], rec[1]) >= th["P5_min_recall"]),
        "P6_no_key_at_least_consensus": bool(n_nokey >= th["P6_min_flagged"] and cons[1] and nokey[1]
                                             and Fraction(nokey[0], nokey[1]) >= Fraction(cons[0], cons[1])),
        "P7_strength_matters": bool(b_s1[1] and b_s5[1] and b_s1[0] / b_s1[1] > b_s5[0] / b_s5[1]),
    }
