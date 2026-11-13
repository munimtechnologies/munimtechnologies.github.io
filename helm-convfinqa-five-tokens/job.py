# SPDX-License-Identifier: Apache-2.0
# Audit 117 check job (MV2 of Munim, Inc.; made with AI agents).
# Downloads the pinned ConvFinQA data.zip that HELM's ConvFinQACalcScenario uses, rebuilds each
# instance's gold exactly as HELM does (str(dic["annotation"]["exe_ans"])), and counts how many golds
# a 5-token answer can reach. Publishes counts only, no dataset text.
import argparse
import io
import json
import os
import re
import statistics
import sys
import time
import urllib.request
import zipfile
from collections import Counter

sys.set_int_max_str_digits(0)

from convfinqa_check import (  # noqa: E402
    MAX_TOKENS,
    _strip_string,
    digit_split_min_tokens,
    digit_split_truncate,
    float_equiv,
    natural_form,
    shortest_form,
)

URL = "https://github.com/czyssrs/ConvFinQA/raw/cf3eed2d5984960bf06bb8145bcea5e80b0222a6/data.zip"
SPLITS = {"valid": "dev_turn.json", "train": "train_turn.json"}  # HELM: VALID_SPLIT -> dev_turn.json (main split)


def download(url, tries=4):
    last = None
    for i in range(tries):
        try:
            with urllib.request.urlopen(url, timeout=120) as r:
                return r.read()
        except Exception as e:  # network hiccup
            last = e
            time.sleep(5 * (i + 1))
    raise RuntimeError(f"download failed: {last!r}")


def load_tokenizers():
    encs = {}
    try:
        import tiktoken  # optional; installed in setup

        for name in ("cl100k_base", "o200k_base"):
            try:
                encs[name] = tiktoken.get_encoding(name)
            except Exception as e:
                print(f"[tiktoken] {name} unavailable: {e!r}")
    except Exception as e:
        print(f"[tiktoken] not available: {e!r}")
    return encs


def gold_of(dic):
    ann = dic.get("annotation", {})
    if "exe_ans" in ann:
        return str(ann["exe_ans"]), "annotation"
    if "exe_ans" in dic:
        return str(dic["exe_ans"]), "top_level"
    return None, "missing"


def last_question(dic):
    ann = dic.get("annotation", {})
    dial = ann.get("cur_dial") or []
    return dial[-1] if dial else ""


def summarise(records, encs):
    n = len(records)
    out = {"n": n}
    out["gold_location"] = dict(Counter(loc for _, loc, _ in records))
    golds = [g for g, _, _ in records if g is not None]
    numeric = [g for g in golds if _strip_string(g) is not None]
    nonnum = [g for g in golds if _strip_string(g) is None]
    out["numeric"] = len(numeric)
    out["non_numeric"] = len(nonnum)
    out["non_numeric_values"] = dict(Counter(g if len(g) <= 8 else "<other>" for g in nonnum))
    out["self_credit"] = int(sum(float_equiv(g, g) for g in golds))

    lb_short = Counter()
    lb_nat = Counter()
    decimals = Counter()
    reach_short = reach_nat = 0
    abs_ge_1000 = 0
    for g in numeric:
        s = shortest_form(g)
        nat = natural_form(g)
        a = digit_split_min_tokens(s)
        b = digit_split_min_tokens(nat)
        lb_short[min(a, 12)] += 1
        lb_nat[min(b, 12)] += 1
        reach_short += a <= MAX_TOKENS
        reach_nat += b <= MAX_TOKENS
        decimals[len(s.split(".")[1]) if "." in s else 0] += 1
        if abs(_strip_string(g)) >= 1000:
            abs_ge_1000 += 1
    out["digit_split_min_tokens_shortest"] = {str(k): v for k, v in sorted(lb_short.items())}
    out["digit_split_min_tokens_natural"] = {str(k): v for k, v in sorted(lb_nat.items())}
    out["decimals_in_shortest_form"] = {str(k): v for k, v in sorted(decimals.items())}
    out["digit_split_reachable_shortest"] = reach_short
    out["digit_split_reachable_natural"] = reach_nat
    out["digit_split_ceiling_shortest"] = round(reach_short / n, 4) if n else None
    out["digit_split_ceiling_natural"] = round(reach_nat / n, 4) if n else None
    out["abs_ge_1000"] = abs_ge_1000

    # Fixed answers scored with HELM's float_equiv against every gold (non-numeric golds score 0).
    strategies = {
        "gold_string": lambda g: g,
        "natural_form": natural_form,
        "shortest_form": lambda g: shortest_form(g) or g,
        "digit_split_5_natural": lambda g: digit_split_truncate(natural_form(g)),
        "digit_split_5_shortest": lambda g: digit_split_truncate(shortest_form(g) or g),
        "round_2dp": lambda g: (f"{_strip_string(g):.2f}" if _strip_string(g) is not None else g),
        "thousands_separator": lambda g: (f"{_strip_string(g):,}" if _strip_string(g) is not None else g),
    }
    scores = {}
    for name, f in strategies.items():
        try:
            scores[name] = int(sum(float_equiv(f(g), g) for g in golds))
        except Exception as e:
            scores[name] = f"ERROR {e!r}"
    out["fixed_answer_credits"] = scores

    # Percent-worded final questions whose gold is a fraction below 1 in absolute value.
    pct = [(g, q) for g, _, q in records if g is not None and re.search(r"percent|%", q, re.I)]
    pct_num = [g for g, _ in pct if _strip_string(g) is not None]
    out["percent_questions"] = len(pct)
    out["percent_questions_gold_abs_lt_1"] = sum(abs(_strip_string(g)) < 1 for g in pct_num)
    out["percent_questions_gold_abs_ge_1"] = sum(abs(_strip_string(g)) >= 1 for g in pct_num)

    tok = {}
    for name, enc in encs.items():
        over = over_sp = 0
        credit5 = 0
        lens = []
        for g in numeric:
            nat = natural_form(g)
            ids = enc.encode(nat)
            lens.append(len(ids))
            over += len(ids) > MAX_TOKENS
            over_sp += len(enc.encode(" " + nat)) > MAX_TOKENS
            credit5 += float_equiv(enc.decode(ids[:MAX_TOKENS]), g) == 1.0
        tok[name] = {
            "natural_over_5": over,
            "space_natural_over_5": over_sp,
            "credit_first_5_tokens_of_natural": credit5,
            "median_tokens_natural": statistics.median(lens) if lens else None,
            "max_tokens_natural": max(lens) if lens else None,
        }
    out["tiktoken"] = tok
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", default="out")
    args = ap.parse_args()
    os.makedirs(args.out_dir, exist_ok=True)

    raw = download(URL)
    print(f"[data] {len(raw)} bytes")
    zf = zipfile.ZipFile(io.BytesIO(raw))
    names = [n for n in zf.namelist() if not n.startswith("__MACOSX")]
    encs = load_tokenizers()
    results = {"source": URL, "max_tokens": MAX_TOKENS, "splits": {}}
    for split, fname in SPLITS.items():
        hits = [n for n in names if n.endswith("/" + fname) or n == fname]
        if not hits:
            print(f"[{split}] {fname} not found in zip")
            results["splits"][split] = {"error": "file not found"}
            continue
        data = json.loads(zf.read(hits[0]).decode("utf-8"))
        records = []
        for dic in data:
            g, loc = gold_of(dic)
            records.append((g, loc, last_question(dic)))
        s = summarise(records, encs)
        results["splits"][split] = s
        print(f"[{split}] {json.dumps(s, sort_keys=True)}")

    v = results["splits"].get("valid", {})
    if "n" in v:
        print(
            f"[headline] valid n={v['n']} numeric={v['numeric']} non_numeric={v['non_numeric']} "
            f"digit-split reachable (shortest form)={v['digit_split_reachable_shortest']} "
            f"ceiling={v['digit_split_ceiling_shortest']} (natural form {v['digit_split_ceiling_natural']}) "
            f"credits {v['fixed_answer_credits']}"
        )
    with open(os.path.join(args.out_dir, "results.json"), "w") as f:
        json.dump(results, f, indent=1, sort_keys=True)


if __name__ == "__main__":
    main()
