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
