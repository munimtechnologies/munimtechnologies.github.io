# SPDX-License-Identifier: Apache-2.0
# Audit 102 (helm-math-classic-regrade), second run of the pre-registered job.
# MV2 of Munim, Inc.; made by AI agents working in MV2's name.
"""Run the UNCHANGED pre-registered audit 102 code with Python's integer-string limit lifted.

The first run (helm-math-classic-regrade-v1, 2026-11-12 15:46-15:51 UTC) stopped with a ValueError in
grade102.value(): one archived model output contained a 5,760-digit number, and Python 3.11+ refuses to convert
integer strings longer than 4,300 digits by default (sys.set_int_max_str_digits). Nothing had been graded or
written. This wrapper fetches the four code files from the commit that published the pre-registration
(d402882b5694a64e7ebdcb6ebb5b4ab4b824b7bf), runs their unit tests, checks that a 5,760-digit number now converts,
and runs job.py as before. The only change is sys.set_int_max_str_digits(0); predictions, thresholds and code are
as frozen on 2026-11-11.
"""
import argparse
import os
import runpy
import sys
import tempfile
import unittest
import urllib.request

COMMIT = "d402882b5694a64e7ebdcb6ebb5b4ab4b824b7bf"
BASE = ("https://raw.githubusercontent.com/munimtechnologies/munimtechnologies.github.io/"
        + COMMIT + "/helm-math-classic-regrade/")
FILES = ("grade102.py", "cases102.py", "job.py", "test_grade102.py")


def fetch(dest):
    for name in FILES:
        data, last = None, None
        for _ in range(4):
            try:
                req = urllib.request.Request(BASE + name, headers={"User-Agent": "mv2-audit102-v2"})
                with urllib.request.urlopen(req, timeout=120) as r:
                    data = r.read()
                break
            except Exception as e:  # noqa: BLE001 - retried, then reported
                last = e
        if data is None:
            raise SystemExit("[v2] fetch failed: %s %r" % (name, last))
        with open(os.path.join(dest, name), "wb") as fh:
            fh.write(data)
        print("[v2] fetched %s (%d bytes)" % (name, len(data)), flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", required=True)
    args = ap.parse_args()
    sys.set_int_max_str_digits(0)  # the only change from v1
    dest = tempfile.mkdtemp(prefix="audit102-")
    fetch(dest)
    sys.path.insert(0, dest)
    os.chdir(dest)
    suite = unittest.defaultTestLoader.discover(dest, pattern="test_grade102.py", top_level_dir=dest)
    res = unittest.TextTestRunner(verbosity=2).run(suite)
    if not res.wasSuccessful():
        raise SystemExit("[v2] pre-registered unit tests failed")
    import grade102  # noqa: E402 - fetched above
    big = "9" * 5760
    if grade102.value(big) != int(big):
        raise SystemExit("[v2] long-number check failed")
    print("[v2] long-number check ok; running the pre-registered job.py", flush=True)
    os.makedirs(args.out_dir, exist_ok=True)
    sys.argv = [os.path.join(dest, "job.py"), "--out-dir", args.out_dir]
    runpy.run_path(sys.argv[0], run_name="__main__")


if __name__ == "__main__":
    main()
