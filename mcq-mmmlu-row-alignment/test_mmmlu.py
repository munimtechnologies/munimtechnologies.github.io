"""Unit tests for audit 73 (stdlib only). Every expected value was traced by hand. Apache-2.0."""

import unittest

import align as al
import cases73 as c
import mmmlu as mm


def _fixture_rows():
    en = mm.english_rows(c.FIXTURE_EN_RECORDS)
    xx, tally = mm.mmmlu_rows(en, c.FIXTURE_MM_RECORDS)
    by_subject = {}
    for r in en:
        by_subject.setdefault(r["subject"], []).append(r)
    return en, xx, tally, by_subject


class TestRows(unittest.TestCase):
    def test_canon_subject(self):
        self.assertEqual(mm.canon_subject("college_mathematics_test.csv_sw-KE.csv"), "college_mathematics")
        self.assertEqual(mm.canon_subject("security_studies_test-sw-KE.csv"), "security_studies")
        self.assertEqual(mm.canon_subject(" abstract_algebra "), "abstract_algebra")
        self.assertEqual(mm.canon_subject("high_school_world_history"), "high_school_world_history")
        self.assertEqual(mm.canon_subject(None), "")

    def test_digest(self):
        self.assertEqual(mm.digest("q ", ["a", "b"]), mm.digest("q", ["a", "b "]))
        self.assertNotEqual(mm.digest("q", ["a", "b"]), mm.digest("q", ["b", "a"]))
        self.assertEqual(len(mm.digest("q", [])), 16)

    def test_english_rows(self):
        en, _, _, _ = _fixture_rows()
        self.assertEqual([r["sample_id"] for r in en], c.FIXTURE_EN_IDS)
        self.assertEqual([r["key"] for r in en], c.FIXTURE_EN_KEYS)
        self.assertEqual([r["fp"] for r in en], c.FIXTURE_EN_FPS)
        self.assertIsNone(mm.english_rows([{"subject": "s", "question": "q", "choices": [], "answer": 7}])[0]["key"])
        self.assertIsNone(mm.english_rows([{"subject": "s", "question": "q", "choices": [], "answer": True}])[0]["key"])

    def test_mmmlu_rows(self):
        en, xx, tally, _ = _fixture_rows()
        self.assertEqual(tally, c.FIXTURE_MM_TALLY)
        self.assertEqual([r["key"] for r in xx], c.FIXTURE_MM_KEYS)
        self.assertEqual([r["sample_id"] for r in xx], c.FIXTURE_EN_IDS)
        short, t2 = mm.mmmlu_rows(en[:2], c.FIXTURE_MM_RECORDS)
        self.assertEqual(len(short), 2)
        self.assertEqual(t2["n"], 6)


class TestCompare(unittest.TestCase):
    def test_compare_language(self):
        _, xx, _, by_subject = _fixture_rows()
        total, cells, mis, flagged, fmap = mm.compare_language(by_subject, xx, c.FIXTURE_FLAG_MIN, c.FIXTURE_FOCUS)
        self.assertEqual(total, c.FIXTURE_TOTAL)
        self.assertEqual(cells, {"s1": c.FIXTURE_S1_REPORT})
        self.assertEqual(sorted(mis), c.FIXTURE_MISALIGNED)
        self.assertEqual(flagged, c.FIXTURE_FLAGGED)
        self.assertEqual(fmap, c.FIXTURE_FOCUS_MAPPING)

    def test_identity_has_no_misaligned(self):
        en, _, _, by_subject = _fixture_rows()
        total, cells, mis, flagged, _ = mm.compare_language(by_subject, en, 1, "s1")
        self.assertEqual((total["misaligned"], total["key_differs_same_id"], cells, mis, flagged), (0, 0, {}, set(), []))
        self.assertEqual(total["aligned"], 5)

    def test_inherit(self):
        _, xx, _, by_subject = _fixture_rows()
        _, _, mis, _, _ = mm.compare_language(by_subject, xx, c.FIXTURE_FLAG_MIN, c.FIXTURE_FOCUS)
        gm = [mm.gm_row(r) for r in c.FIXTURE_GM_RECORDS]
        self.assertEqual(mm.inherit_compare(gm, {r["sample_id"]: r for r in xx}, mis), c.FIXTURE_INHERIT)

    def test_sum_keys_cover_counters(self):
        self.assertEqual(set(mm.SUM_KEYS) - set(al.COUNTERS),
                         {"n", "no_fingerprint", "count_differs", "mapped", "aligned", "misaligned"})


if __name__ == "__main__":
    unittest.main()
