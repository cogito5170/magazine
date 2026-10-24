import json
import math
import os
import unittest

import numpy as np

from edas.config import load_config
from edas.modules.layout import SPECS as LS
from edas.pdf.extract import open_document
from edas.schema import make_result
from edas.typo.counterfactual import experiment_a, experiment_b, find_run
from edas.typo.outlines import FileFontOutlines, PdfFontOutlines

from .helpers import TMP, bilingual

ALT = "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf"


class TestSchema(unittest.TestCase):
    def test_null_and_nan(self):
        r = make_result(LS["A06"], None)
        self.assertEqual(r.validation_status.value, "not_measured")
        r = make_result(LS["A06"], float("nan"))
        self.assertIsNone(r.value)
        r = make_result(LS["A06"], 0.5, source="raster")
        self.assertEqual(r.measurement_type.value, "estimated")


@unittest.skipUnless(os.path.exists(ALT), "DejaVu Serif not installed")
class TestCounterfactual(unittest.TestCase):
    def test_experiments(self):
        path, _ = bilingual()
        doc = open_document(path, load_config())
        run = find_run(doc, 0, "Observe")
        fk = run["font_key"]
        fonts = {fk: PdfFontOutlines(doc.fonts[fk].handle, fk), "DejaVuSerif": FileFontOutlines(ALT, 0, "ObservexH")}
        ma = experiment_a(fonts, "Observe", os.path.join(TMP, "A"), original=fk, as_set_positions_em=run["positions_em"])
        self.assertEqual(ma["experiment"], "A_typeface")
        self.assertEqual(len(ma["pairs"]), 1)
        h = {s["font"]: s["metric_height_em"] * s["px_per_em"] for s in ma["stimuli"]}
        self.assertTrue(all(abs(v - 96) < 1e-6 for v in h.values()))     # equal cap height
        mb = experiment_b(path, doc, run, fonts, os.path.join(TMP, "B"), original=fk)
        self.assertEqual(mb["experiment"], "B_page")
        self.assertGreaterEqual(mb["conditions"]["removed_text_objects"], 1)
        with open(path, "rb") as fh:
            import hashlib
            self.assertEqual(hashlib.sha256(fh.read()).hexdigest(), doc.sha256)   # source untouched


if __name__ == "__main__":
    unittest.main()
