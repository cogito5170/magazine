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

photos = [
    Photo("night", crop=(212, 39, 668, 997), outfit=(450, 599, 560, 799), person=(240, 329, 590, 997),
          label="night, riverside"),
    Photo("park", crop=(1120, 217, 2000, 639), outfit=(1730, 417, 1820, 597), person=(1680, 267, 1840, 639),
          label="dusk, amusement park"),
    Photo("shop", crop=(1113, 757, 1312, 1127), outfit=(1160, 882, 1220, 1032), person=(1130, 772, 1260, 1127),
          label="day, shop front"),
    Photo("rock", crop=(1370, 760, 1944, 1127), outfit=(1800, 860, 1910, 1030), person=(1600, 775, 1944, 1127),
          label="seaside, rocks"),
]
texts = {
    "title": "MATCH.",
    "kicker": "FOUR PLACES, FOUR OUTFITS.",
    "body_ko": ["나는 그날 갈 장소에 옷의 톤을 맞춘다.", "장소가 틀이라면, 옷은 그 틀을 채우는 조합이다."],
    "running_head": "FROM THE INSIDE  —  PART 2 MATCH",
    "folio": "11",
}
spec = compose(SRC, photos, texts, OUT)
with open(f"{OUT}/match_redesign_spec.json", "w", encoding="utf-8") as fh:
    json.dump(spec, fh, ensure_ascii=False, indent=2)
print(json.dumps({k: spec[k] for k in ("palette", "contrast")}, ensure_ascii=False))
for k, v in spec["photos"].items():
    print(k, v["scale"], v["upscaled"], v["place_hex"], v["outfit_hex"], round(v["delta_e00_place_outfit"], 1))
