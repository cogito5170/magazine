import os
import unittest

import numpy as np
from reportlab.pdfgen import canvas

from edas.config import load_config
from edas.modules import layout
from edas.modules.common import PageContext
from edas.pdf.extract import open_document
from edas.synth import make_blank_pdf, make_flattened_pdf

from .helpers import TMP, analysed, synthetic


class TestExtraction(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.path, cls.truth = synthetic()
        cls.doc = open_document(cls.path, load_config())

    def test_page_and_images(self):
        for pm, tp in zip(self.doc.pages, self.truth["pages"]):
            self.assertEqual((pm.width, pm.height), (600.0, 800.0))
            self.assertEqual(len(pm.images), 1)
            np.testing.assert_allclose(pm.images[0].box, tp["images"][0]["box"], atol=0.01)
            self.assertAlmostEqual(pm.images[0].effective_ppi[0], tp["images"][0]["ppi"], delta=1.0)

    def test_font_sizes(self):
        sizes = sorted({round(c.size, 2) for c in self.doc.pages[0].chars if not c.text.isspace()})
        self.assertEqual(sizes, [10.0, 30.0])

    def test_source_file_unchanged(self):
        import hashlib
        with open(self.path, "rb") as fh:
            self.assertEqual(hashlib.sha256(fh.read()).hexdigest(), self.doc.sha256)

    def test_rotated_page_coordinates(self):
        p = os.path.join(TMP, "rot.pdf")
        c = canvas.Canvas(p, pagesize=(400, 200))
        c.rect(10, 20, 30, 40, fill=1, stroke=0)          # user space, y up
        c.setPageRotation(90)
        c.showPage()
        c.save()
        import pypdf
        raw = pypdf.PdfReader(p).pages[0]
        wu, hu = float(raw.mediabox.width), float(raw.mediabox.height)
        self.assertEqual(int(raw.get("/Rotate")), 90)
        pm = open_document(p, load_config()).pages[0]
        self.assertEqual((pm.width, pm.height), (hu, wu))          # displayed size is swapped
        box = pm.vectors[0].box
        # 90° clockwise display: user (x, y) -> top-left (y, x)
        np.testing.assert_allclose(box, (20, 10, 60, 40), atol=0.05)

    def test_raster_fallback_blank_and_flattened(self):
        cfg = load_config()
        b = os.path.join(TMP, "blank.pdf")
        make_blank_pdf(b)
        self.assertEqual(open_document(b, cfg).pages[0].extraction_mode, "raster")
        rgb = np.ones((800, 600, 3))
        rgb[100:400, 50:550] = [0.2, 0.4, 0.7]
        f = os.path.join(TMP, "flat.pdf")
        make_flattened_pdf(f, rgb)
        pm = open_document(f, cfg).pages[0]
        self.assertEqual(pm.extraction_mode, "raster")
        self.assertTrue(all(o.source == "raster" for o in pm.objects))
        imgs = [o for o in pm.objects if o.kind == "image"]
        self.assertEqual(len(imgs), 1)
        np.testing.assert_allclose(imgs[0].box, (50, 100, 550, 400), atol=3)


class TestLayout(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.path, cls.truth = synthetic()
        cls.res, cls.doc, cls.ex = analysed()

    def test_grid_recovered(self):
        g = self.truth["grid"]
        for pa in self.res.pages:
            v = pa.get("A02").value
            self.assertEqual(v["n"], g["n"])
            self.assertAlmostEqual(v["m_l"], g["m_l"], delta=0.5)
            self.assertAlmostEqual(v["c"], g["c"], delta=1.0)
            self.assertAlmostEqual(v["g"], g["g"], delta=1.0)
            self.assertLess(abs(pa.get("A02").details["columns"]["identity_residual"]), 1e-6)

    def test_occupancies(self):
        for pa, tp in zip(self.res.pages, self.truth["pages"]):
            b = tp["images"][0]["box"]
            self.assertAlmostEqual(pa.get("A07").value, (b[2] - b[0]) * (b[3] - b[1]) / (600 * 800), places=5)
            self.assertAlmostEqual(pa.get("A09").value, 1 - pa.get("A06").value)
            for pid in ("A06", "A07", "A08", "A09"):
                self.assertTrue(0 <= pa.get(pid).value <= 1)

    def test_margins(self):
        m = self.res.pages[0].get("A04").value
        self.assertAlmostEqual(m["M_l"], 50 / 600, places=3)
        self.assertAlmostEqual(m["M_r"], 50 / 600, places=3)
        self.assertAlmostEqual(m["M_b"], 60 / 800, places=3)
        self.assertAlmostEqual(self.res.pages[0].get("A05").value["horizontal"], 0, places=3)

    def test_undefined_for_single_object(self):
        p = os.path.join(TMP, "one.pdf")
        c = canvas.Canvas(p, pagesize=(300, 300))
        c.rect(50, 50, 100, 100, fill=1, stroke=0)
        c.showPage()
        c.save()
        pm = open_document(p, load_config()).pages[0]
        res, _ = layout.analyze_page(PageContext(pm, load_config()))
        a10 = next(r for r in res if r.parameter_id == "A10")
        self.assertIsNone(a10.value)
        self.assertEqual(a10.validation_status.value, "undefined")

    def test_reproducible(self):
        from edas.pipeline import RunOptions, analyze
        r2, d2, _ = analyze(self.path, load_config(), RunOptions(with_candidates=False))
        a = [p.value for p in self.res.pages[0].parameters]
        b = [p.value for p in r2.pages[0].parameters]
        self.assertEqual(a, b)


if __name__ == "__main__":
    unittest.main()
