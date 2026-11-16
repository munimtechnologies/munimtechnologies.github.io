"""Audit 125 helpers: HELM Classic's MS MARCO (regular track) RR@10 re-computed with each passage's answer-only log
probability.

HELM Classic ranks MS MARCO passages one prompt at a time ("Does the passage answer the query? Answer:"). Its
RankingMetric (helm v0.3.0, metrics/ranking_metrics.py) sorts a query's passages by (class, score): answers "Yes"
first, most probable first, by the STORED completion log probability; then "No", least probable first; then anything
else. Audit 104 found that for 21 HELM Classic adapters the stored log probability and token list run past the stop
sequence ("\\n") at which the scored text was cut. MS MARCO's run spec uses the same stop and 5 output tokens, so for
such adapters the ranking score includes the newlines and the start of the next "Passage:". This module rebuilds
HELM's per-query order and RR@10 from the stored values (the gate) and with the log probability cut at the stop.

Record-level token functions (token_bytes, decode_tokens, keep_count) and the aggregate helpers are unchanged from
audits 104 and 124. Standard library only. Apache-2.0. Authored by AI agents working in the name of MV2, Munim, Inc.
"""

import hashlib
import math
import re

# ----- Token text -> bytes (GPT-2 byte-level BPE, SentencePiece, AI21 newline token); unchanged from audit 104 -----


def _bytes_to_unicode():
    """GPT-2's byte <-> printable-character table (openai/gpt-2 encoder.py), returned as char -> byte."""
    bs = list(range(ord("!"), ord("~") + 1)) + list(range(ord("\xa1"), ord("\xac") + 1)) + \
        list(range(ord("\xae"), ord("\xff") + 1))
    cs = bs[:]
    n = 0
    for b in range(256):
        if b not in bs:
            bs.append(b)
            cs.append(256 + n)
            n += 1
    return {chr(c): b for b, c in zip(bs, cs)}


BYTE_DECODER = _bytes_to_unicode()
_BYTE_TOKEN = re.compile(r"<0x([0-9A-Fa-f]{2})>")


def token_bytes(t):
    """Bytes of one token string as HELM stored it: '<0xHH>' byte tokens, '<|newline|>' -> newline, SentencePiece
    '\\u2581' -> space, GPT-2 byte characters ('\\u0120' space, '\\u010a' newline) -> their byte, anything else -> UTF-8."""
    m = _BYTE_TOKEN.fullmatch(t or "")
    if m:
        return bytes([int(m.group(1), 16)])
    out = bytearray()
    for ch in (t or "").replace("<|newline|>", "\n"):
        if ch == "▁":
            out += b" "
        elif ch in BYTE_DECODER:
            out.append(BYTE_DECODER[ch])
        else:
            out += ch.encode("utf-8")
    return bytes(out)


def decode_tokens(texts):
    return b"".join(token_bytes(t) for t in texts).decode("utf-8", "replace")


def keep_count(texts, stops):
    """Number of leading tokens kept: the largest k whose decoded prefix contains no stop sequence."""
    stops = [s for s in (stops or []) if s]
    if not stops:
        return len(texts)
    for k in range(1, len(texts) + 1):
        d = decode_tokens(texts[:k])
        if any(s in d for s in stops):
            return k - 1
    return len(texts)


# ----- One passage request (new) -----

MISSING_RESULT_TEXT = "missing"
CORRECT_OUTPUT = "Yes"
WRONG_OUTPUT = "No"


def _num(v):
    return float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else 0.0


def first_completion(rs):
    """HELM's get_model_output_logprob: the FIRST completion's text and stored log probability ('missing', 0.0 when
    there is no result or no completion), plus its token list [(text, logprob)]."""
    res = (rs or {}).get("result")
    comps = res.get("completions") if isinstance(res, dict) else None
    if res and comps:
        c = comps[0] if isinstance(comps[0], dict) else {}
        toks = [((t or {}).get("text") or "", _num((t or {}).get("logprob"))) for t in (c.get("tokens") or [])]
        text = c.get("text")
        return {"text": text if isinstance(text, str) else "", "logprob": _num(c.get("logprob")), "tokens": toks}
    return {"text": MISSING_RESULT_TEXT, "logprob": 0.0, "tokens": []}


def answer_only(comp, stops):
    """(answer-only log probability, overrun, kept, consistent). Overrun: some stored token lies at or past the
    first stop; the answer-only log probability is then the sum over the tokens before it, else the stored value.
    consistent: the kept tokens decode to the stored text (both stripped)."""
    texts = [t for t, _ in comp["tokens"]]
    k = keep_count(texts, stops)
    consistent = decode_tokens(texts[:k]).strip() == comp["text"].strip()
    if k < len(texts):
        return sum(lp for _, lp in comp["tokens"][:k]), True, k, consistent
    return comp["logprob"], False, k, consistent


def ref_tags(ref):
    """(gold, relevance, rank) as HELM's create_ranking_object reads a reference's tags: gold = 'correct' tag;
    a tag containing 'relevance' gives relevance, else one containing 'rank' gives rank (value after '=')."""
    tags = [t for t in ((ref or {}).get("tags") or []) if isinstance(t, str)]
    relevance = rank = None
    for t in tags:
        if "relevance" in t:
            relevance = int(t.split("=")[1])
        elif "rank" in t:
            rank = int(t.split("=")[1])
    return "correct" in tags, relevance, rank


# ----- HELM's binary ranking and RR@k (transcribed) -----


def score_key(text, lp):
    """object_to_score_binary_ranking: (2, lp) for 'yes', (1, -lp) for 'no', (0, -lp) otherwise, on the stripped,
    lower-cased output."""
    out = (text or "").strip().lower()
    if out == CORRECT_OUTPUT.strip().lower():
        return (2, lp)
    if out == WRONG_OUTPUT.strip().lower():
        return (1, -1 * lp)
    return (0, -1 * lp)


def model_order(objs, lp_key):
    """compute_model_relevance_binary_ranking: the passages sorted by score_key, descending; Python's sort is stable
    under reverse=True, so equal keys keep reference order (objs must come in reference order)."""
    return sorted(objs, key=lambda o: score_key(o["text"], o[lp_key]), reverse=True)


def rr_at(ordered, k, rank_limit=None):
    """pytrec_eval recip_rank on HELM's run cut to its top k: 1 / position of the first passage with relevance >= 1
    among the first k; with rank_limit, only passages whose BM25 rank tag is set and <= rank_limit are kept first
    (order unchanged). 0.0 when none."""
    run = [o for o in ordered if not rank_limit or (o["rank"] and o["rank"] <= rank_limit)]
    for i, o in enumerate(run[:k]):
        if (o["relevance"] or 0) >= 1:
            return 1.0 / (i + 1)
    return 0.0


def first_gold_position(ordered):
    """1-based position of the first passage with relevance >= 1 in the full order; None when there is none."""
    for i, o in enumerate(ordered):
        if (o["relevance"] or 0) >= 1:
            return i + 1
    return None


def gold_outside(objs, topk):
    """True when some relevant passage has no BM25 rank tag or a rank above topk (added to the candidates from the
    qrels only)."""
    return any((o["relevance"] or 0) >= 1 and not (o["rank"] and o["rank"] <= topk) for o in objs)


# ----- One run -----

EVAL_SPLIT = "valid"
K = 10
TOPK = 30
REC_KEYS = ("records", "overrun", "consistent", "overrun_consistent", "tokens", "lp_mismatch")
GROUP_KEYS = ("groups", "no_gold", "gold_outside_topk", "rr_changed", "first_gold_moved")
TRIAL_KEYS = ("p10", "t10", "pk", "tk")


def stops_of(state):
    return list(((state or {}).get("adapter_spec") or {}).get("stop_sequences") or [])


def summarize_run(state, cap_samples=2):
    """Group the unperturbed valid-split passage requests of one run by (instance id, trial); the first request per
    (id, trial, reference_index) is kept. Per group, rank the passages as HELM does with the stored log probability
    (p) and with the answer-only one (t), and compute RR@10 on all candidates and on the BM25 top 30 only.
    trials {trial: {p10, t10, pk, tk: [per-group values]}}; rec / grp: counts; excess: stored minus answer-only log
    probability per overrun record; samples: up to cap_samples overrun records (job log only)."""
    stops = stops_of(state)
    counts = {"request_states": 0, "perturbed": 0, "not_eval": 0, "no_reference_index": 0, "duplicate": 0, "kept": 0}
    rec = {k: 0 for k in REC_KEYS}
    groups, seen, excess, samples = {}, set(), [], []
    for rs in (state or {}).get("request_states") or []:
        if not isinstance(rs, dict):
            continue
        counts["request_states"] += 1
        inst = rs.get("instance") or {}
        if inst.get("perturbation") is not None:
            counts["perturbed"] += 1
            continue
        if inst.get("split") != EVAL_SPLIT:
            counts["not_eval"] += 1
            continue
        refs = inst.get("references") or []
        ri = rs.get("reference_index")
        if not isinstance(ri, int) or isinstance(ri, bool) or not 0 <= ri < len(refs):
            counts["no_reference_index"] += 1
            continue
        key = (inst.get("id"), rs.get("train_trial_index", 0), ri)
        if key in seen:
            counts["duplicate"] += 1
            continue
        seen.add(key)
        counts["kept"] += 1
        gold, rel, rank = ref_tags(refs[ri])
        comp = first_completion(rs)
        t_lp, over, kept, cons = answer_only(comp, stops)
        rec["records"] += 1
        rec["tokens"] += len(comp["tokens"])
        rec["consistent"] += 1 if cons else 0
        if over:
            rec["overrun"] += 1
            rec["overrun_consistent"] += 1 if cons else 0
            excess.append(comp["logprob"] - t_lp)
            if abs(comp["logprob"] - sum(lp for _, lp in comp["tokens"])) > 1e-6:
                rec["lp_mismatch"] += 1
            if len(samples) < cap_samples:
                samples.append({"key": key, "text": comp["text"], "tokens": [t for t, _ in comp["tokens"]],
                                "kept": kept, "stored_lp": comp["logprob"], "answer_lp": t_lp, "gold": gold})
        groups.setdefault(key[:2], []).append({"ri": ri, "gold": gold, "relevance": rel, "rank": rank,
                                               "text": comp["text"], "p": comp["logprob"], "t": t_lp})
    grp = {k: 0 for k in GROUP_KEYS}
    trials = {}
    for gk in sorted(groups, key=lambda x: (str(x[0]), x[1])):
        objs = sorted(groups[gk], key=lambda o: o["ri"])
        grp["groups"] += 1
        if first_gold_position(objs) is None:
            grp["no_gold"] += 1
        if gold_outside(objs, TOPK):
            grp["gold_outside_topk"] += 1
        op, ot = model_order(objs, "p"), model_order(objs, "t")
        vals = {"p10": rr_at(op, K), "t10": rr_at(ot, K), "pk": rr_at(op, K, TOPK), "tk": rr_at(ot, K, TOPK)}
        if vals["p10"] != vals["t10"]:
            grp["rr_changed"] += 1
        if first_gold_position(op) != first_gold_position(ot):
            grp["first_gold_moved"] += 1
        acc = trials.setdefault(gk[1], {k: [] for k in TRIAL_KEYS})
        for k in TRIAL_KEYS:
            acc[k].append(vals[k])
    return {"counts": counts, "rec": rec, "grp": grp, "trials": trials, "excess": excess, "samples": samples,
            "stops": stops}


def trial_mean(trials, key):
    """(mean over trials of the per-trial mean of `key`, number of trials): HELM's take_mean per trial, then the
    merged stat's mean. (None, 0) without groups."""
    xs = [sum(v[key]) / len(v[key]) for _, v in sorted(trials.items()) if v[key]]
    return (sum(xs) / len(xs), len(xs)) if xs else (None, 0)


def run_class(overrun, n):
    """'overrun' when at least half of the records carry tokens past the stop, else 'clean'; None without records."""
    if not n:
        return None
    return "overrun" if 2 * overrun >= n else "clean"


# ----- Run names and HELM files -----

SCENARIO = "msmarco"
DROP_PREFIXES = ("track=", "valid_topk=")


def _parts(run):
    return run.split(":", 1)[1].split(",") if ":" in run else run.split(",")


def scenario_of(run):
    return run.split(":", 1)[0] if ":" in run else ""


def is_selected(run):
    """A canonical MS MARCO regular-track run."""
    p = _parts(run)
    return scenario_of(run) == SCENARIO and "track=regular" in p and "data_augmentation=canonical" in p


def adapter_of(run):
    return ",".join(p for p in _parts(run)
                    if p != "data_augmentation=canonical" and not p.startswith(DROP_PREFIXES))


def model_part(name):
    i = name.find("model=")
    return name[i + len("model="):] if i >= 0 else ""


def select_runs(run_suites):
    return {r: s for r, s in (run_suites or {}).items() if is_selected(r)}


def stat_entry(stats, name, split):
    """{count, sum, mean} of the unperturbed stat `name` on `split` in a HELM stats.json list (None when absent)."""
    for s in stats or []:
        if not isinstance(s, dict):
            continue
        nm = s.get("name") or {}
        if (nm.get("name") == name and nm.get("split") == split and nm.get("perturbation") is None
                and nm.get("sub_split") is None):
            return {"count": s.get("count"), "sum": s.get("sum"), "mean": s.get("mean")}
    return None


def slim_hook(d):
    """json object_hook that drops what the audit never reads: prompts, top_logprobs, instance inputs and the
    passage text of every reference (its tags are kept)."""
    d.pop("prompt", None)
    d.pop("top_logprobs", None)
    if "references" in d and "input" in d:
        d.pop("input")
    if "tags" in d and "output" in d:
        d.pop("output")
    return d


# ----- Ranks, matching, summaries (audit 104's, ranks now higher-is-better) -----


def ranks_high(values):
    """Higher is better: rank = 1 + the number of entries strictly higher."""
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


def group_values(group_doc, name):
    """Numeric values of the column whose header is exactly `name` in a group page's first table."""
    if not isinstance(group_doc, list) or not group_doc or not isinstance(group_doc[0], dict):
        return None
    t = group_doc[0]
    header = t.get("header") or []
    col = next((j for j, h in enumerate(header) if isinstance(h, dict) and str(h.get("value") or "") == name), None)
    if col is None:
        return None
    out = []
    for row in t.get("rows") or []:
        if isinstance(row, list) and len(row) > col and isinstance(row[col], dict):
            v = row[col].get("value")
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                out.append(float(v))
    return out


def match_cells(ours, published, tol):
    """How many of our cell values find a distinct published value within tol (greedy, both sorted)."""
    pub = sorted(published)
    used = [False] * len(pub)
    hit = 0
    for v in sorted(ours.values()):
        for j, p in enumerate(pub):
            if not used[j] and abs(p - v) <= tol:
                used[j] = True
                hit += 1
                break
    return hit


def median(xs):
    s = sorted(xs)
    n = len(s)
    if not n:
        return None
    return s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2


def stable_hash(text):
    return int(hashlib.sha256(text.encode("utf-8")).hexdigest()[:12], 16)


# ----- Verdicts -----

EXPECTED_OVERRUN = ("together_bloom", "together_gpt-j-6b", "together_gpt-neox-20b", "together_opt-175b",
                    "together_opt-66b")


def verdicts(s):
    """The eight pre-registered predictions (True = HELD) from the job's statistics `s` with keys fixtures,
    runs_listed, runs_included, published, matched, overrun_set, overrun, median_excess, overrun_records,
    overrun_consistent, delta_hits, better, worse, movers, groups_overrun, groups_changed."""
    return {
        "P1": (bool(s["fixtures"]) and s["runs_listed"] > 0 and s["runs_included"] * 10 >= 9 * s["runs_listed"]
               and s["published"] > 0 and s["matched"] * 10 >= 9 * s["published"]),
        "P2": sorted(s["overrun_set"]) == sorted(EXPECTED_OVERRUN),
        "P3": s["median_excess"] is not None and s["median_excess"] <= -0.1,
        "P4": s["overrun"] > 0 and 2 * s["delta_hits"] >= s["overrun"],
        "P5": s["overrun_records"] > 0 and s["overrun_consistent"] * 20 >= 19 * s["overrun_records"],
        "P6": s["better"] > s["worse"],
        "P7": s["movers"] >= 1,
        "P8": s["groups_overrun"] > 0 and s["groups_changed"] * 10 >= s["groups_overrun"],
    }
