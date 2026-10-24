"""Join ChaosNLI's 100-vote records back to the original SNLI/MNLI 5-annotator examples and census the
100-vote outcome by original agreement level.

Data (job.json data_urls, downloaded to --data-dir):
  - snli_1.0.zip              -> read snli_1.0_dev.jsonl + snli_1.0_test.jsonl (both have annotator_labels)
  - multinli_1.0.zip          -> read multinli_1.0_dev_matched.jsonl + ..._dev_mismatched.jsonl

ChaosNLI 100-annotation records (uid == original pairID) are loaded by this job, not through data_urls,
because the loose-file HF mirror and the Dropbox zip both drop transiently in the sandbox (v1/v2/v3 all
failed on exactly those two sources while SNLI/MNLI cached fine). We instead read ChaosNLI from the HF
auto-converted **parquet** branch (refs/convert/parquet), which is served from the reliable parquet CDN,
downloading it directly with urllib + retries into distinct per-subset filenames in --data-dir (kept in
the data volume for reuse). If a loose chaosNLI_<subset>.jsonl or an official chaosNLI_v1.0.zip is already
present in --data-dir, those are preferred; otherwise the parquet is fetched. Whichever source arrives is
used, so a transient drop on one does not fail the job.

For each ChaosNLI record we look up its original example by uid (== pairID), read the original gold_label
and annotator_labels, and build a joined record. The census (crosslink_census.py) buckets by original
agreement-with-gold (5 / 4 / 3 / "-"=dash) and cross-tabs each bucket against whether the original gold
survives the 100-vote plurality and whether the 100 votes reach a strict majority. Orphans (ChaosNLI uids
with no original match) are reported, never silently dropped.

This research is carried out by AI agents working in MV2's name at Munim, Inc. Apache-2.0.
"""
import argparse
import glob
import json
import os
import shutil
import sys
import time
import urllib.request
import zipfile

import cases
from crosslink_census import census, flatten, no_strict_rate, old_flip_rate, NAMES_3WAY


# ----- original SNLI/MNLI loading -------------------------------------------------------------------

_SNLI_MEMBERS = ("snli_1.0_dev.jsonl", "snli_1.0_test.jsonl")
_MNLI_MEMBERS = ("multinli_1.0_dev_matched.jsonl", "multinli_1.0_dev_mismatched.jsonl")


def _member_wanted(member, wanted):
    base = os.path.basename(member)
    return base in wanted


def _lines_from_zip(zpath, wanted):
    """Yield (member_basename, line) for the wanted .jsonl members inside a zip."""
    with zipfile.ZipFile(zpath) as zf:
        for member in zf.namelist():
            if not member.endswith(".jsonl") or not _member_wanted(member, wanted):
                continue
            with zf.open(member) as fh:
                for raw in fh.read().decode("utf-8").splitlines():
                    yield os.path.basename(member), raw


def _lines_from_loose(data_dir, wanted):
    """Yield (basename, line) for any wanted .jsonl files present loose in data_dir."""
    for path in sorted(glob.glob(os.path.join(data_dir, "*.jsonl"))):
        if not _member_wanted(path, wanted):
            continue
        with open(path, "r", encoding="utf-8") as fh:
            for raw in fh:
                yield os.path.basename(path), raw


def _build_index(data_dir, zip_glob, wanted):
    """pairID -> {'gold':..., 'annotators':[...], 'src':...} for the wanted original files.

    Prefers a zip matching zip_glob; falls back to loose .jsonl files with the wanted basenames.
    """
    index = {}
    dup = 0
    sources = set()
    zips = sorted(glob.glob(os.path.join(data_dir, zip_glob)))
    if zips:
        gen = ((b, ln) for z in zips for (b, ln) in _lines_from_zip(z, wanted))
    else:
        gen = _lines_from_loose(data_dir, wanted)
    for base, raw in gen:
        line = raw.strip()
        if not line:
            continue
        obj = json.loads(line)
        pid = obj.get("pairID")
        if pid is None:
            continue
        sources.add(base)
        if pid in index:
            dup += 1
            continue
        index[pid] = {
            "gold": obj.get("gold_label"),
            "annotators": obj.get("annotator_labels") or [],
            "src": base,
        }
    return index, dup, sorted(sources)


# ----- ChaosNLI loading -----------------------------------------------------------------------------

# HF auto-converted parquet (refs/convert/parquet) for the earino/chaosnli preservation mirror. The
# validation split of each 3-way config carries uid (== original pairID), old_label and label_count
# ([e, n, c] summing to 100). Served from the reliable parquet CDN (the same mechanism QASC uses).
_CHAOS_PARQUET_URLS = {
    "snli": "https://huggingface.co/datasets/earino/chaosnli/resolve/refs%2Fconvert%2Fparquet/snli/validation/0000.parquet",
    "mnli_m": "https://huggingface.co/datasets/earino/chaosnli/resolve/refs%2Fconvert%2Fparquet/mnli_m/validation/0000.parquet",
}


def _parse_chaos_lines(lines):
    """Parse an iterable of raw ChaosNLI jsonl lines into {uid, old, counts} records."""
    recs = []
    for raw in lines:
        line = raw.strip()
        if not line:
            continue
        obj = json.loads(line)
        counts = obj.get("label_count")
        counts = [int(c) for c in counts] if isinstance(counts, list) else []
        recs.append({"uid": obj.get("uid"), "old": obj.get("old_label"), "counts": counts})
    return recs


def _chaos_from_loose(data_dir, basename):
    """Read a loose ChaosNLI jsonl (the HF mirror); None if the file is not present."""
    path = os.path.join(data_dir, basename)
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as fh:
        return _parse_chaos_lines(fh)


def _chaos_from_zip(data_dir, basename):
    """Read a ChaosNLI jsonl member (by basename) from the official chaosNLI_v1.0.zip; None if absent."""
    for fname in sorted(os.listdir(data_dir)):
        low = fname.lower()
        if "chaosnli" not in low or ".zip" not in low:
            continue
        zpath = os.path.join(data_dir, fname)
        try:
            with zipfile.ZipFile(zpath) as zf:
                for member in zf.namelist():
                    if member.endswith(".jsonl") and os.path.basename(member) == basename:
                        with zf.open(member) as fh:
                            text = fh.read().decode("utf-8")
                        return _parse_chaos_lines(text.splitlines())
        except (zipfile.BadZipFile, OSError):
            continue
    return None


def _download_with_retry(url, dest, attempts=4, timeout=120):
    """Download url -> dest with a few retries; True on a non-empty file, else False (logs, never raises)."""
    last = None
    for i in range(attempts):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "mv2-eval-reliability-audit/1.0"})
            with urllib.request.urlopen(req, timeout=timeout) as resp, open(dest, "wb") as out:
                shutil.copyfileobj(resp, out)
            if os.path.exists(dest) and os.path.getsize(dest) > 0:
                return True
        except Exception as exc:  # noqa: BLE001 - best-effort fetch, keep going
            last = exc
            try:
                if os.path.exists(dest):
                    os.remove(dest)
            except OSError:
                pass
        time.sleep(2 * (i + 1))
    print("[warn] download failed after %d attempts: %s (%s)" % (attempts, url, last), file=sys.stderr)
    return False


def _chaos_from_parquet(data_dir, subset):
    """Fetch (once) and read ChaosNLI records for a subset from the HF parquet; None on failure."""
    url = _CHAOS_PARQUET_URLS.get(subset)
    if not url:
        return None
    dest = os.path.join(data_dir, "chaosNLI_%s.parquet" % subset)
    if not (os.path.exists(dest) and os.path.getsize(dest) > 0):
        if not _download_with_retry(url, dest):
            return None
    try:
        import pyarrow.parquet as pq
        table = pq.read_table(dest, columns=["uid", "old_label", "label_count"])
    except Exception as exc:  # noqa: BLE001 - treat an unreadable parquet as "missing"
        print("[warn] parquet read failed for %s: %s" % (dest, exc), file=sys.stderr)
        return None
    recs = []
    for row in table.to_pylist():
        counts = row.get("label_count")
        counts = [int(c) for c in counts] if isinstance(counts, (list, tuple)) else []
        recs.append({"uid": row.get("uid"), "old": row.get("old_label"), "counts": counts})
    return recs


def _chaos_records(data_dir, basename, subset):
    """ChaosNLI records for one subset: prefer a loose jsonl, else the official zip, else HF parquet."""
    recs = _chaos_from_loose(data_dir, basename)
    if recs is None:
        recs = _chaos_from_zip(data_dir, basename)
    if recs is None:
        recs = _chaos_from_parquet(data_dir, subset)
    return recs


def _join(chaos_recs, index, subset):
    """Join ChaosNLI records to original examples; return (joined, n_orphan, orphan_sample)."""
    joined = []
    n_orphan = 0
    orphan_sample = []
    for cr in chaos_recs:
        orig = index.get(cr["uid"])
        if orig is None:
            n_orphan += 1
            if len(orphan_sample) < 10:
                orphan_sample.append(cr["uid"])
            continue
        joined.append({
            "uid": cr["uid"],
            "subset": subset,
            "orig_gold": orig["gold"],
            "annotator_labels": orig["annotators"],
            "old": cr["old"],
            "counts": cr["counts"],
            "names": NAMES_3WAY,
        })
    return joined, n_orphan, orphan_sample


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default="/data")
    ap.add_argument("--out-dir", default="/out")
    args = ap.parse_args()
    os.makedirs(args.out_dir, exist_ok=True)

    # 1. Assert the hand-traced fixture BEFORE touching real data.
    fix = flatten(census(cases.FIXTURE))
    target_met = all(fix[k] == cases.TARGET[k] for k in cases.TARGET)
    print("[fixture] target_met =", target_met)
    for k in cases.TARGET:
        if fix[k] != cases.TARGET[k]:
            print("  MISMATCH %-22s observed=%r target=%r" % (k, fix[k], cases.TARGET[k]))
    if not target_met:
        print("FATAL: fixture does not match hand-traced target", file=sys.stderr)
        sys.exit(2)

    # 2. Build original indexes (SNLI dev+test, MNLI matched+mismatched dev).
    snli_index, snli_dup, snli_src = _build_index(args.data_dir, "snli_1.0*.zip", _SNLI_MEMBERS)
    mnli_index, mnli_dup, mnli_src = _build_index(args.data_dir, "multinli_1.0*.zip", _MNLI_MEMBERS)
    print("[diag] snli index=%d (dup=%d) from %s" % (len(snli_index), snli_dup, snli_src))
    print("[diag] mnli index=%d (dup=%d) from %s" % (len(mnli_index), mnli_dup, mnli_src))
    if not snli_index or not mnli_index:
        print("FATAL: could not build original SNLI/MNLI indexes", file=sys.stderr)
        sys.exit(3)

    # 3. Load ChaosNLI (loose jsonl, else official zip, else HF parquet) and join.
    chaos_snli = _chaos_records(args.data_dir, "chaosNLI_snli.jsonl", "snli")
    chaos_mnli = _chaos_records(args.data_dir, "chaosNLI_mnli_m.jsonl", "mnli_m")
    if chaos_snli is None or chaos_mnli is None:
        print("FATAL: ChaosNLI snli/mnli_m records missing (loose, zip and parquet all unavailable)",
              file=sys.stderr)
        sys.exit(4)

    j_snli, orph_snli, orph_snli_s = _join(chaos_snli, snli_index, "snli")
    j_mnli, orph_mnli, orph_mnli_s = _join(chaos_mnli, mnli_index, "mnli_m")
    joined = j_snli + j_mnli
    n_chaos = len(chaos_snli) + len(chaos_mnli)
    n_orphan = orph_snli + orph_mnli
    coverage = (len(joined) / n_chaos) if n_chaos else 0.0
    print("[diag] chaos snli=%d (orphan=%d) mnli_m=%d (orphan=%d) coverage=%.4f" % (
        len(chaos_snli), orph_snli, len(chaos_mnli), orph_mnli, coverage))
    if orph_snli_s:
        print("[diag] snli orphan sample:", orph_snli_s)
    if orph_mnli_s:
        print("[diag] mnli orphan sample:", orph_mnli_s)

    # 4. Census overall and per subset.
    stats = census(joined)
    flat = flatten(stats)
    per_subset = {
        "snli": flatten(census(j_snli)),
        "mnli_m": flatten(census(j_mnli)),
    }

    # 5. Pre-registered predictions.
    #   P1 (structural): >=99% of ChaosNLI SNLI+MNLI records join to a loaded original example.
    #   P2 (directional, finding either way): unanimous-original examples reach no strict 100-vote
    #       majority LESS often than bare-majority-original ones.
    #   P3 (directional, finding either way): the old gold flips against the 100-vote plurality MORE
    #       often for bare-majority-original examples than for unanimous ones.
    r5_no_strict = no_strict_rate(stats, "5")
    r3_no_strict = no_strict_rate(stats, "3")
    r5_flip = old_flip_rate(stats, "5")
    r3_flip = old_flip_rate(stats, "3")
    predictions = {
        "P1_join_coverage_at_least_99pct": coverage >= cases.MIN_JOIN_COVERAGE,
        "P2_unanimous_less_ambiguous_than_bare_majority": r5_no_strict < r3_no_strict,
        "P3_bare_majority_flips_more_than_unanimous": r3_flip > r5_flip,
    }
    for k, v in predictions.items():
        print("[prediction] %s = %s" % (k, "HELD" if v else "FAILED"))
    print("[diag] no_strict rate  unanimous(5)=%.4f bare(3)=%.4f" % (r5_no_strict, r3_no_strict))
    print("[diag] old-flip rate   unanimous(5)=%.4f bare(3)=%.4f" % (r5_flip, r3_flip))

    rates = {
        "overall": {
            "no_strict_unanimous": r5_no_strict,
            "no_strict_bare_majority": r3_no_strict,
            "no_strict_four": no_strict_rate(stats, "4"),
            "old_flip_unanimous": r5_flip,
            "old_flip_bare_majority": r3_flip,
            "old_flip_four": old_flip_rate(stats, "4"),
        },
    }
    print("[diag] rates =", rates)

    out = {
        "dataset": "ChaosNLI v1.0 (Nie, Zhou, Bansal, EMNLP 2020) joined to the original SNLI 1.0 "
                   "(dev+test) and MultiNLI 1.0 (matched+mismatched dev) examples by uid == pairID. For "
                   "each re-annotated example we read the ORIGINAL gold_label and up to 5 annotator_labels "
                   "and the 100 ChaosNLI votes, and cross-tabulate the 100-vote outcome by original "
                   "agreement level.",
        "chaos_source": "earino/chaosnli HF auto-converted parquet (refs/convert/parquet), downloaded by "
                        "job.py with retries; falls back to a loose jsonl or the official zip if present.",
        "n_chaos_records": n_chaos,
        "n_joined": len(joined),
        "n_orphan": n_orphan,
        "join_coverage": coverage,
        "orphan_sample": {"snli": orph_snli_s, "mnli_m": orph_mnli_s},
        "index_sizes": {"snli": len(snli_index), "mnli_m": len(mnli_index)},
        "expected_subset_rows": cases.EXPECTED_SUBSET_ROWS,
        "chaos_subset_rows": {"snli": len(chaos_snli), "mnli_m": len(chaos_mnli)},
        "synthetic_corpus": {"target_met": target_met, "observed": fix, "target": cases.TARGET},
        "overall": {"totals": stats["totals"], "buckets": stats["buckets"]},
        "per_subset": per_subset,
        "rates": rates,
        "predictions": predictions,
        "examples_orig_unanimous_no_strict": stats["examples_orig_unanimous_no_strict"],
        "examples_bare_majority_flipped": stats["examples_bare_majority_flipped"],
        "note": "Buckets are by how many of the up to 5 ORIGINAL annotators agreed with the original gold "
                "(5 unanimous, 4, 3 bare majority) or 'dash' when the original gold was '-' (no majority). "
                "For each bucket we count how often ChaosNLI's old gold still equals the 100-vote plurality "
                "(old_eq_plur) vs flips (old_diff_plur), and how often the 100 votes reach a strict (>50) "
                "majority (strict) vs none (no_strict). P1 is a structural coverage bet; P2 and P3 are "
                "directional (a finding either way), with the exact per-bucket rates reported. ChaosNLI is "
                "CC BY-NC 4.0; this audit reads the official release and reports counts, it does not "
                "redistribute it.",
    }
    out_path = os.path.join(args.out_dir, "results.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1, ensure_ascii=False, default=str)
    print("[done] wrote", out_path)


if __name__ == "__main__":
    main()
