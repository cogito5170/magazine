"""Redesign of the 'PART 2 MATCH' spread (user-supplied image) with the photo-led method.

Coordinates refer to the supplied 2000x1231 spread image.  Clean crops avoid
the pixel-block overlays (no inpainting); outfit rectangles sample garment
colour; person boxes are excluded from the place-tone estimate.
"""
import json
import sys

from edas.mood.photo_led import Photo, compose

SRC = sys.argv[1] if len(sys.argv) > 1 else "output/match/original_spread.png"
OUT = sys.argv[2] if len(sys.argv) > 2 else "output/match"

sys.path.insert(0, __import__("os").path.dirname(__file__))
from match_spread_data import PHOTOS as photos, TEXTS as texts  # noqa: E402

spec = compose(SRC, photos, texts, OUT)
with open(f"{OUT}/match_redesign_spec.json", "w", encoding="utf-8") as fh:
    json.dump(spec, fh, ensure_ascii=False, indent=2)
print(json.dumps({k: spec[k] for k in ("palette", "contrast")}, ensure_ascii=False))
for k, v in spec["photos"].items():
    print(k, v["scale"], v["upscaled"], v["place_hex"], v["outfit_hex"], round(v["delta_e00_place_outfit"], 1))
