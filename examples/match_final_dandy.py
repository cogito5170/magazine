"""Render the final MATCH spread: NOCTURNE at round-I intensity, contemporary-art methods, soft-dandy mood.

    sh scripts/fetch_fonts.sh
    PYTHONPATH=.:examples python3 examples/match_final_dandy.py
"""
import datetime as dt
import json
import os

from PIL import Image

from match_spread_data import PHOTOS, TEXTS
from edas.mood.contemporary import nocturne_dandy

OUT = "output/match/final_dandy"
APPROVAL = {"approver": "user", "decision": "direction approved", "scope": "MATCH spread, one final draft",
            "instructions": ["이정도가 가장 적당해", "내말은 과감하면서 현대 예술 기법을 따르도록",
                             "좋은데 무드 바꿔. 무드를 댄디하게", "부드러움 댄디"]}

if __name__ == "__main__":
    src = Image.open("output/match/original_spread.png").convert("RGB")
    crops = {p.key: src.crop((p.crop[0] + 3, p.crop[1] + 3, p.crop[2] - 3, p.crop[3] - 3)) for p in PHOTOS}
    page, spec = nocturne_dandy(crops, TEXTS)
    os.makedirs(OUT, exist_ok=True)
    page.save(f"{OUT}/MATCH_final_dandy.png", optimize=True)
    page.save(f"{OUT}/MATCH_final_dandy.pdf", "PDF", resolution=144.0)
    spec.update(generated=dt.datetime.now(dt.timezone.utc).isoformat(), approval=APPROVAL)
    with open(f"{OUT}/final_spec.json", "w") as fh:
        json.dump(spec, fh, ensure_ascii=False, indent=2)
    print(f"{OUT}/MATCH_final_dandy.png")
