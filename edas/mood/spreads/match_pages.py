"""MATCH, two pages (cover "DESIGN + MOOD" and the four-place spread): regions and verbatim copy.

Source: `sources/match_pages.png`, a 1054×1318 screenshot of both pages, one above the other
(cover y 0–650, spread y 660–1318).  Coordinates were read on 3× enlarged crops of that file.
The spread's four photographs are the same ones as in `sources/match_spread.png` (2000×1231), which is
about 1.9× sharper, so the spread takes them from there (`match.PHOTOS`).
"""
from .match import PHOTOS  # noqa: F401  (the spread's photographs, sharper source)

COVER_SOURCE = "sources/match_pages.png"
SPREAD_SOURCE = "sources/match_spread.png"

# cut-out figures standing on the cover's paper; floor (terracotta) starts at y 488
FIGURES = {
    "form": {"box": (508, 98, 620, 528), "seed": (565, 300), "key_tol": 10, "label": "dress form"},
    "model": {"box": (768, 92, 940, 520), "seed": (850, 260), "key_tol": 14, "label": "model, outfit"},
}
FLOOR_Y = 488

COVER_TEXTS = {
    "title": "MATCH",
    "quote": ["\"옷의 색감, 원단, 디자인을", "맞춘다. 그날 갈 장소에", "옷의 무드를 맞춘다."],
    "design": "DESIGN +",
    "mood": "MOOD",
}

SPREAD_TEXTS = {
    "title": "MATCH.",
    "head": "주변과 조화되는 지원자",
    "body": "원색보다 한 톤 낮은 색을 좋아한다. 가라앉은 색은 혼자 드러나지 않고 주변과 어우러진다. "
            "내 색을 앞세우기보다, JAJU의 톤에 녹아들어 JAJU의 정체성이 보이게 하는 VMD가 되겠다.",
}
# copy notes: the cover quote opens with a quotation mark that is never closed (kept as is).
