"""The approved mood spreads must never regress: each re-render from its source must be pixel-identical."""
import json
import os
import unittest

from edas.mood import fonts
from edas.mood.spreads import WORKS, render, verify

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APPROVED = os.path.join(ROOT, "edas", "mood", "spreads", "approved.json")


class TestApprovedSpreads(unittest.TestCase):
    def test_every_work_has_an_approved_hash(self):
        with open(APPROVED) as fh:
            ref = json.load(fh)
        self.assertEqual(set(ref), set(WORKS))

    def test_pixel_identical(self):
        missing = [k for k, ok in fonts.status().items() if not ok]
        self.assertFalse(missing, f"fonts missing ({missing}); run `edas mood fonts --install` — without them the "
                                  f"approved spreads cannot be reproduced")
        with open(APPROVED) as fh:
            ref = json.load(fh)
        for name in WORKS:
            with self.subTest(work=name):
                src = os.path.join(ROOT, ref[name]["source"])
                page, _ = render(name, src)
                check = verify(name, src, page)
                self.assertTrue(check["source_matches"], f"{name}: source image changed")
                self.assertTrue(check["pixels_match"], f"{name}: {check['verdict']}; approved with "
                                                       f"{ref[name]['rendered_with']}")


class TestMoodCli(unittest.TestCase):
    def test_new_and_grid(self):
        import tempfile
        from PIL import Image
        from edas.cli import main
        with tempfile.TemporaryDirectory() as tmp:
            img = os.path.join(tmp, "s.png")
            Image.new("RGB", (300, 200), (120, 90, 60)).save(img)
            cwd = os.getcwd()
            os.chdir(tmp)
            try:
                main(["mood", "new", "job", "--image", img, "--mood", "고요"])
                with open(os.path.join("output", "job", "brief.json")) as fh:
                    brief = json.load(fh)
                self.assertEqual(brief["mood"], "고요")
                self.assertEqual(brief["size"], [300, 200])
                main(["mood", "grid", img, "--region", "10", "10", "110", "60", "--zoom", "2", "-o", "g.png"])
                self.assertEqual(Image.open("g.png").size, (236, 136))
            finally:
                os.chdir(cwd)


if __name__ == "__main__":
    unittest.main()


class TestReadAndPrint(unittest.TestCase):
    def test_read_cues_and_print_boxes(self):
        import tempfile
        import pypdf
        from PIL import Image
        from edas.mood.read import measure, print_pdf
        night = measure(Image.new("RGB", (100, 80), (12, 14, 20)))
        self.assertIn("dark/night", night["cues"])
        day = measure(Image.new("RGB", (100, 80), (235, 230, 220)))
        self.assertIn("bright/day", day["cues"])
        with tempfile.TemporaryDirectory() as tmp:
            png = os.path.join(tmp, "p.png")
            Image.new("RGB", (2551, 3579), (200, 190, 180)).save(png)
            rep = print_pdf([png], os.path.join(tmp, "o.pdf"), (210, 297), 3)
            self.assertFalse(rep["pages"][0]["below_convention"])
            page = pypdf.PdfReader(os.path.join(tmp, "o.pdf")).pages[0]
            self.assertAlmostEqual(float(page.trimbox.width) * 25.4 / 72, 210, places=1)
            self.assertAlmostEqual(float(page.mediabox.width) * 25.4 / 72, 216, places=1)

    def test_pdf_extract(self):
        import tempfile
        from edas.mood.read import extract_pdf, read_pdf
        from edas.synth import make_test_pdf
        with tempfile.TemporaryDirectory() as tmp:
            pdf = os.path.join(tmp, "t.pdf")
            make_test_pdf(pdf, pages=2)
            man = extract_pdf(pdf, os.path.join(tmp, "x"))
            self.assertEqual(len(man["pages"]), 2)
            self.assertTrue(all(i.get("effective_ppi") for p in man["pages"] for i in p["images"]))
            self.assertEqual(len(read_pdf(pdf)), 2)
