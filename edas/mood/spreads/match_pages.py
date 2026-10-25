"""MATCH, two pages supplied together: the cover "DESIGN + MOOD" and the spread "주변과 조화되는 지원자".

Source: `sources/match_pages.png`, a 1054×1318 screenshot of both pages, one above the other
(cover y 0–650, spread y 660–1318).  Figure boxes were read with `edas mood grid --zoom 2`
(dress form x 518–608, y 104–519; model x 775–928, y 95–517; floor y 488–650).
The spread's four photographs are the same as in `sources/match_spread.png` (2000×1231, about 1.9× sharper),
so the spread takes them from there (`match.PHOTOS`).  Copy is transcribed verbatim from 4× crops.
"""
from .match import PHOTOS  # noqa: F401

COVER_SOURCE = "sources/match_pages.png"
SPREAD_SOURCE = "sources/match_spread.png"

# the cover's two figures, cropped as prints with the paper and floor they stand on in the source
PRINTS = {
    "form": (478, 78, 650, 600),
    "model": (746, 78, 962, 600),
}
# palette sampled from the source (medians): cover paper, the blue panel, the floor, the model's black sleeve
SRC_PAPER, SRC_BLUE, SRC_FLOOR, SRC_SLEEVE = (239, 232, 226), (130, 150, 181), (197, 158, 128), (8, 15, 12)

COVER_TEXTS = {
    "title": "MATCH",
    "quote": ["\"옷의 색감, 원단, 디자인을", "맞춘다. 그날 갈 장소에", "옷의 무드를 맞춘다."],
    "kicker": "DESIGN + MOOD",
}
SPREAD_TEXTS = {
    "title": "MATCH.",
    "head": "주변과 조화되는 지원자",
    "body": "원색보다 한 톤 낮은 색을 좋아한다. 가라앉은 색은 혼자 드러나지 않고 주변과 어우러진다. "
            "내 색을 앞세우기보다, JAJU의 톤에 녹아들어 JAJU의 정체성이 보이게 하는 VMD가 되겠다.",
}
# copy note: the cover quote opens with a quotation mark that is never closed (kept as is, reported).

# cover, read through the NOCTURNE structure: the hero is the cover's own scene (both figures on paper and
# floor, cropped to the left page's 0.81 aspect); the three prints are details named by the quote:
# 원단 (the quilted vest), 디자인 (the dress form), 색감 (trousers on the floor)
COVER_HERO = (527, 0, 1054, 650)
COVER_PRINTS = {"park": (770, 180, 940, 261), "shop": (505, 100, 620, 317), "rock": (775, 418, 935, 520)}  # slot aspects as the spread
