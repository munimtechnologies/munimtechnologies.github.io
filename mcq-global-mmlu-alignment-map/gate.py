"""Fixture gates for audit 74 (standard library only, shared by job.py and the unit tests). Apache-2.0.
Authored by AI agents working in the name of MV2, Munim, Inc."""

import align as al
import amap
import cases
import cases74 as c74


def fixture72():
    """Audit 72's hand-traced fixture, unchanged."""
    rep, mapping = al.compare_subject(cases.FIXTURE_EN, cases.FIXTURE_XX)
    return {"report": rep, "mapping": mapping,
            "agreement": al.content_agreement(mapping, cases.FIXTURE_MAP_B),
            "lite": al.lite_compare(cases.FIXTURE_LITE_ROWS, cases.FIXTURE_LITE_FULL, cases.FIXTURE_LITE_EN,
                                    cases.FIXTURE_LITE_MISALIGNED)}


def fixture74():
    en, xx = c74.FIXTURE_EN, c74.FIXTURE_XX
    en_by_id = {r["sample_id"]: r for r in en}
    m1, s1 = amap.capped_align(en, xx, 1)
    _, s2 = amap.capped_align(en, xx, 2)
    mapping, _ = al.align(en, xx)
    rows = amap.build_map(en, xx, mapping, c74.MAP_INFERRED)
    return {
        "cap1_mapping": m1, "cap1_stats": s1, "cap1_keys": amap.key_report(en_by_id, xx, m1), "cap2_stats": s2,
        "offsets": amap.offsets_from(mapping),
        "infer": amap.infer(c74.INFER_N, c74.INFER_OFFSETS, c74.INFER_TARGETS),
        "infer_edge": amap.infer(*c74.INFER_EDGE[:3]),
        "infer_range": amap.infer(*c74.INFER_RANGE[:3]),
        "loo": amap.leave_one_out(c74.INFER_N, c74.INFER_OFFSETS),
        "map": rows, "summary": amap.summarize(rows),
    }


def check():
    """(ok, list of differing keys) for both fixtures."""
    diffs = []
    f72 = fixture72()
    for k in cases.FIXTURE_TARGET:
        if f72.get(k) != cases.FIXTURE_TARGET[k]:
            diffs.append(("72", k, f72.get(k), cases.FIXTURE_TARGET[k]))
    f74 = fixture74()
    for k in c74.FIXTURE_TARGET:
        if f74.get(k) != c74.FIXTURE_TARGET[k]:
            diffs.append(("74", k, f74.get(k), c74.FIXTURE_TARGET[k]))
    return not diffs, diffs
