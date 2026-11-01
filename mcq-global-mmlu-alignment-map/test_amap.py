"""Unit tests for audit 74 (stdlib only). Every expected value was traced by hand. Apache-2.0.
Authored by AI agents working in the name of MV2, Munim, Inc."""

import unittest

import align as al
import amap
import cases
import cases74 as c74
import gate


class TestCapped(unittest.TestCase):
    def test_cap1(self):
        m, st = amap.capped_align(c74.FIXTURE_EN, c74.FIXTURE_XX, 1)
        self.assertEqual(m, c74.FIXTURE_CAP1_MAPPING)
        self.assertEqual(st, c74.FIXTURE_CAP1_STATS)
        self.assertEqual(st["mapped"] + st["no_fingerprint"] + st["count_differs"] + st["over_cap"], st["n"])

    def test_cap_large_equals_align(self):
        m_cap, st = amap.capped_align(c74.FIXTURE_EN, c74.FIXTURE_XX, 1000)
        m_al, st_al = al.align(c74.FIXTURE_EN, c74.FIXTURE_XX)
        self.assertEqual(m_cap, m_al)
        self.assertEqual(st["over_cap"], 0)
        for k in st_al:
            self.assertEqual(st[k], st_al[k])

    def test_cap2(self):
        _, st = amap.capped_align(c74.FIXTURE_EN, c74.FIXTURE_XX, 2)
        self.assertEqual(st, c74.FIXTURE_CAP2_STATS)

    def test_key_report(self):
        en_by_id = {r["sample_id"]: r for r in c74.FIXTURE_EN}
        m, _ = amap.capped_align(c74.FIXTURE_EN, c74.FIXTURE_XX, 1)
        self.assertEqual(amap.key_report(en_by_id, c74.FIXTURE_XX, m), c74.FIXTURE_CAP1_KEYS)
        self.assertEqual(amap.key_report(en_by_id, c74.FIXTURE_XX, {}),
                         {"misaligned": 0, "mis_key_equals_content": 0, "mis_key_equals_id": 0})


class TestInfer(unittest.TestCase):
    def test_offsets(self):
        self.assertEqual(amap.offsets_from(cases.FIXTURE_MAPPING), c74.FIXTURE_OFFSETS)

    def test_infer(self):
        self.assertEqual(amap.infer(c74.INFER_N, c74.INFER_OFFSETS, c74.INFER_TARGETS), c74.INFER_EXPECTED)

    def test_infer_edges(self):
        self.assertEqual(amap.infer(*c74.INFER_EDGE[:3]), c74.INFER_EDGE[3])
        self.assertEqual(amap.infer(*c74.INFER_RANGE[:3]), c74.INFER_RANGE[3])
        self.assertEqual(amap.infer(5, {}, [0, 1]), {})

    def test_constant_shift(self):
        # every matched row holds the question 3 places earlier; the gaps get the same shift
        offsets = {j: -3 for j in range(3, 20) if j not in (7, 12, 13)}
        self.assertEqual(amap.infer(20, offsets, [7, 12, 13]), {7: 4, 12: 9, 13: 10})

    def test_loo(self):
        self.assertEqual(amap.leave_one_out(c74.INFER_N, c74.INFER_OFFSETS), c74.LOO_EXPECTED)
        offsets = {j: -3 for j in range(3, 20)}
        self.assertEqual(amap.leave_one_out(20, offsets), {"tested": 17, "made": 15, "agree": 15})


class TestMap(unittest.TestCase):
    def test_build_map(self):
        rows = amap.build_map(c74.FIXTURE_EN, c74.FIXTURE_XX, cases.FIXTURE_MAPPING, c74.MAP_INFERRED)
        self.assertEqual(rows, c74.MAP_EXPECTED)
        self.assertEqual(amap.summarize(rows), c74.SUMMARY_EXPECTED)


class TestGate(unittest.TestCase):
    def test_both_fixtures(self):
        ok, diffs = gate.check()
        self.assertTrue(ok, diffs)


if __name__ == "__main__":
    unittest.main()
