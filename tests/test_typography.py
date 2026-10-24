import unittest

from .helpers import analysed


def P(res, page, pid):
    return res.pages[page].get(pid)


class TestTypography(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.res, cls.doc, _ = analysed("synthetic")
        cls.bres, cls.bdoc, cls.bex = analysed("bilingual")

    def test_ratios(self):
        self.assertAlmostEqual(P(self.res, 0, "B03").value, 3.0, places=3)          # 30 / 10
        self.assertAlmostEqual(P(self.res, 0, "B12").value["median"], 1.4, places=3)  # 14 / 10
        self.assertEqual(P(self.res, 0, "B14").value, 2)

    def test_contrast_black_on_white(self):
        self.assertAlmostEqual(P(self.res, 0, "B18").value["median"], 21.0, delta=0.5)

    def test_stroke_contrast_serif_vs_sans(self):
        b5 = P(self.res, 0, "B05").value["by_font"]
        self.assertGreater(b5["Times-Bold"], b5["Helvetica"])

    def test_legibility_not_faked(self):
        b19 = P(self.res, 0, "B19")
        self.assertIsNone(b19.value)
        self.assertEqual(b19.validation_status.value, "not_measured")

    def test_hangul_visually_larger_than_latin_caps(self):
        v = P(self.bres, 0, "BK05").value["page_tight_box_ratio"]["median"]
        self.assertGreater(v, 1.1)    # same nominal size, different visual size

    def test_hangul_strata_and_complexity(self):
        bk03 = self.bres.get_doc("BK03").value
        prof = next(iter(bk03.values()))
        self.assertGreaterEqual(len(prof["strata_covered"]), 3)
        rel = next(iter(self.bres.get_doc("BK10").value.values()))
        self.assertIsNotNone(rel["slope_per_component"])

    def test_identification_and_no_model(self):
        ident = P(self.bres, 0, "BK02").value
        self.assertEqual(ident["korean"][0]["status"], "verified")
        for pid in ("BK11", "BK12"):
            self.assertIsNone(P(self.bres, 0, pid).value)
            self.assertEqual(P(self.bres, 0, pid).validation_status.value, "no_model")


class TestAestheticGuard(unittest.TestCase):
    """Regression for the 'large, high-contrast title => beautiful' error: a 61 pt,
    21:1 title must not receive any aesthetic score without preference data."""

    @classmethod
    def setUpClass(cls):
        cls.res, cls.doc, _ = analysed("bilingual")

    def test_title_functional_facts_kept_apart(self):
        tx = self.res.pages[0].get("TX01").value
        line = next(d for d in tx["display_lines"] if d["text"].startswith("Observe"))
        self.assertAlmostEqual(line["functional_facts"]["size_pt"], 61.0, places=1)
        self.assertIsNone(line["aesthetic_verdict"])

    def test_all_aesthetic_outputs_null_without_data(self):
        for pid in ("TC01",):
            self.assertIsNone(self.res.pages[0].get(pid).value)
        for pid in ("TE01", "TE02", "F01", "F02", "F03", "F04", "F05", "F06", "F07", "F08", "F16"):
            self.assertIsNone(self.res.get_doc(pid).value, pid)

    def test_morphology_present_but_not_a_score(self):
        ta = self.res.get_doc("TA01")
        self.assertIn("descriptors are observations, not aesthetic quality", ta.notes)


if __name__ == "__main__":
    unittest.main()
