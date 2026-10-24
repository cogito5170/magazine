"""Render 'WHERE PEOPLE STOP ?' in the rapport mood.

    sh scripts/fetch_fonts.sh
    PYTHONPATH=.:examples python3 examples/stop_rapport.py   # expects output/stop/original.jpg
"""
import json
import os

from PIL import Image

from stop_spread_data import CELLS, TEXTS
from edas.mood.rapport import rapport_spread

OUT = "output/stop/rapport"

if __name__ == "__main__":
    src = Image.open("output/stop/original.jpg").convert("RGB")
    page, spec = rapport_spread(src, CELLS, TEXTS)
    os.makedirs(OUT, exist_ok=True)
    page.save(f"{OUT}/STOP_rapport.png", optimize=True)
    page.save(f"{OUT}/STOP_rapport.pdf", "PDF", resolution=144.0)
    spec["instructions"] = ["이것도", "무드는 “라포틱하게”"]
    with open(f"{OUT}/spec.json", "w") as fh:
        json.dump(spec, fh, ensure_ascii=False, indent=2, default=list)
    print(f"{OUT}/STOP_rapport.png")
