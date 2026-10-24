"""Four further mood treatments of the 'PART 2 MATCH' spread (same photos, same copy)."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from match_spread_data import PHOTOS, TEXTS  # noqa: E402

from edas.mood.variants import render_all  # noqa: E402

SRC = sys.argv[1] if len(sys.argv) > 1 else "output/match/original_spread.png"
OUT = sys.argv[2] if len(sys.argv) > 2 else "output/match/variants"
specs = render_all(SRC, PHOTOS, TEXTS, OUT)
with open(os.path.join(OUT, "variants_spec.json"), "w", encoding="utf-8") as fh:
    json.dump(specs, fh, ensure_ascii=False, indent=2, default=float)
for k, s in specs.items():
    print(k, s["mood"], s["palette"], "upscaled:", s["upscaled_any_photo"])
