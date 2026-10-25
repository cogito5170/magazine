"""The cover the user liked (022 red bars, "이건 좋아") must keep rendering pixel-identical."""
import hashlib
import json
import unittest
from dataclasses import replace

from PIL import Image

from edas.mood.kinds import bars_v1
from edas.mood.moodmachine import DANDY
from edas.mood.spreads import match_pages as mp

LAYER = {"paper": (16, 16, 16), "ink": (255, 255, 255), "camel": (204, 20, 30), "saturation": 0.0,
         "title_face": "inter", "title_weight": "Black", "title_mode": "solid", "title_color": (255, 255, 255),
         "body_face": "sans", "body_weight": "Bold", "caption_face": "mono", "shadow": "none",
         "halation": (255, 1, (255, 255, 255), 0.0), "slit_amp": 0}
STRUCTURE = {"kind": "bars", "hero": "park, black and white, both pages edge to edge",
             "bar_color": [204, 20, 30], "text_color": [255, 255, 255]}


class UserLikedKrugerCover(unittest.TestCase):
    def test_pixels(self):
        want = json.load(open("docs/user_liked_kruger_cover.json"))["pixels_sha256"]
        L = replace(DANDY, name="red bars", strip_key="park", strip_col=(0.5, 0.1, 0.95), **LAYER)
        cv = Image.open(mp.COVER_SOURCE).convert("RGB")
        cc = {"night": cv.crop(mp.COVER_HERO), **{k: cv.crop(b) for k, b in mp.COVER_PRINTS.items()}}
        c = mp.COVER_TEXTS
        page, _ = bars_v1.render(cc, {"title": c["title"], "kicker": c["kicker"], "body": " ".join(c["quote"]),
                                      "cover": True, "structure": STRUCTURE}, L, mp.COVER_PERSONS, H=1233)
        self.assertEqual(hashlib.sha256(page.tobytes()).hexdigest(), want)


if __name__ == "__main__":
    unittest.main()
