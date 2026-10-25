"""Mood writer: proposes mood layers to the editor through the mood-relay mailbox (docs/mood_relay.md).

The writer never renders and never grades itself. It writes one spec.json per idea; the editor renders
it in the approved structure and the code judge (edas/mood/judge.py) decides, default REJECT.

    python3 scripts/mood_writer.py                 # write every card not yet in the mailbox
    python3 scripts/mood_writer.py --list          # print the cards, write nothing
    python3 scripts/mood_writer.py --relay DIR     # another mailbox folder

Rules the cards keep (from docs/mood_library.md and the user's rejections):
  * not palette-only: every card moves at least two non-palette levers (photo technique, title, shadow, faces)
  * none of the dandy signature: no Richter strip title, no slit-scan amplitude, no soft JPEG shadow
  * no colour chips, no ΔE numbers on the page, no rational grid, no generated or inpainted photo
  * each card names one art technique and a source that was opened and read in this session (`quote`)

Ideas that need a structure change (the levers cannot express them) are kept in STRUCTURE and are not
sent: the approved structure is fixed until the user opens it.
"""
from __future__ import annotations

import argparse
import json
import os
import re

RELAY = "/mnt/project-files/mood-relay"
OFF = [255, 1, [255, 255, 255], 0.0]                        # halation with zero strength

CARDS = [
    dict(slug="cyanotype", name="cyanotype specimen", mood="청사진: 네 장소를 프러시안 블루 한 톤으로 맞춘 표본",
         technique="Anna Atkins, Photographs of British Algae (1843), cyanotype photograms",
         sources=["https://aperture.org/blog/anna-atkins/"],
         quote="Atkins printed some six thousand cyanotype photogram exposures on hand-treated paper",
         layer={"paper": [238, 240, 242], "ink": [22, 48, 96], "taupe": [120, 150, 190], "camel": [40, 70, 120],
                "light": [226, 234, 240], "note": [200, 214, 230],
                "hero_fx": [["duotone", [14, 34, 80], [226, 234, 240]]],
                "print_fx": [["duotone", [14, 34, 80], [226, 234, 240]]],
                "title_face": "italic", "title_mode": "solid", "title_color": [22, 48, 96],
                "body_face": "serif", "body_weight": "Regular", "caption_face": "serif_it",
                "shadow": "none", "halation": OFF, "slit_amp": 0, "grain": [0.03, 2.0]}),
    dict(slug="kruger", name="red bar", mood="크루거: 흑백 사진 위 빨간 띠와 굵은 기울임 고딕, 카피가 선언처럼",
         technique="Barbara Kruger, black-and-white photographs with white-on-red Futura Bold Oblique",
         sources=["https://whitney.org/artists/2635"],
         quote="black-and-white photographs ... white-on-red Futura Bold Oblique or Helvetica Ultra Condensed",
         layer={"paper": [250, 250, 248], "ink": [16, 16, 16], "taupe": [16, 16, 16], "camel": [204, 20, 30],
                "saturation": 0.0, "hero_matte": [0, 255], "print_matte": [0, 255],
                "hero_fx": [["duotone", [10, 10, 10], [246, 246, 246]]],
                "print_fx": [["duotone", [10, 10, 10], [246, 246, 246]]],
                "title_face": "inter", "title_weight": "Black", "title_mode": "solid", "title_color": [204, 20, 30],
                "body_face": "sans", "body_weight": "Bold", "caption_face": "mono",
                "shadow": "none", "halation": OFF, "slit_amp": 0, "grain": [0.008, 1.0]}),
    dict(slug="provoke", name="are bure boke", mood="프로보크: 거칠고 흔들리고 초점 나간 흑백, 갱지",
         technique="Daido Moriyama / Provoke (late 1960s), are-bure-boke",
         sources=["https://thephotographersgallery.org.uk/node/2317"],
         quote="'are, bure, boke' - or 'grainy, blurry, out of focus' ... often associated with the Provoke era",
         layer={"paper": [214, 212, 204], "ink": [20, 20, 20], "taupe": [90, 90, 88], "camel": [60, 60, 58],
                "saturation": 0.0, "hero_matte": [0, 232], "print_matte": [0, 232],
                "hero_fx": [["duotone", [6, 6, 6], [236, 236, 232]], ["blur_ramp", 6]],
                "print_fx": [["duotone", [6, 6, 6], [236, 236, 232]], ["blur_ramp", 3]],
                "title_face": "sans", "title_weight": "Black", "title_mode": "solid", "title_color": [20, 20, 20],
                "body_face": "sans", "body_weight": "Medium", "caption_face": "mono",
                "shadow": "threshold", "halation": OFF, "slit_amp": 0, "grain": [0.09, 2.6]}),
    dict(slug="polke-raster", name="raster", mood="폴케: 신문 망점을 크게 키워 사진이 점으로 풀리는 지면",
         technique="Sigmar Polke, Rasterbilder (1960s), magnified newsprint dots",
         sources=["https://en.wikipedia.org/wiki/Sigmar_Polke"],
         quote="exploit the raster-dot technique of printing as a way as of subverting and bringing into question the apparent truth",
         layer={"paper": [232, 224, 200], "ink": [30, 28, 26], "taupe": [150, 140, 116], "camel": [90, 80, 64],
                "hero_fx": [["halftone", 14, [30, 28, 26]]], "print_fx": [["halftone", 7, [30, 28, 26]]],
                "title_face": "inter", "title_weight": "Bold", "title_mode": "outline", "title_color": [30, 28, 26],
                "body_face": "sans", "body_weight": "Regular", "caption_face": "mono",
                "shadow": "none", "halation": OFF, "slit_amp": 0, "grain": [0.02, 1.2]}),
    dict(slug="weingart-film", name="film montage", mood="바인가르트: 리스 필름을 겹친 듯 반전과 거친 망점, 시안 별색",
         technique="Wolfgang Weingart, layered film collages with rough halftone screens (Basel, 1970s-80s)",
         sources=["https://eyeondesign.aiga.org/museum-of-design-zurich-unveils-the-weingart-archive/"],
         quote="rough, fragmented dot screens ... The low resolution of the screens reveals the photo-mechanical process",
         layer={"paper": [246, 246, 244], "ink": [18, 18, 18], "taupe": [0, 120, 190], "camel": [0, 110, 176],
                "hero_fx": [["solarize", 150], ["halftone", 9, [0, 120, 190]]],
                "print_fx": [["solarize", 150], ["halftone", 5, [18, 18, 18]]],
                "title_face": "inter", "title_weight": "Thin", "title_mode": "outline", "title_color": [0, 120, 190],
                "body_face": "sans", "body_weight": "Light", "caption_face": "mono", "marks": True,
                "shadow": "threshold", "halation": OFF, "slit_amp": 0, "grain": [0.01, 1.0]}),
    dict(slug="tintype", name="wet plate", mood="습판: 어두운 금속판 위 은빛 단색, 가운데만 선명하고 가장자리는 흐름",
         technique="Sally Mann, Proud Flesh (2009), wet-plate collodion with its flaws kept",
         sources=["https://brooklynrail.org/2009/11/artseen/sally-mann-proud-flesh/"],
         quote="The collodion 'skin' of the negative, with all its flaws, is prominent in these prints",
         layer={"paper": [38, 36, 34], "ink": [226, 220, 206], "taupe": [90, 84, 76], "camel": [176, 160, 130],
                "light": [226, 220, 206], "note": [176, 160, 130], "saturation": 0.0,
                "hero_matte": [20, 214], "print_matte": [20, 214],
                "hero_fx": [["duotone", [20, 18, 16], [214, 206, 186]], ["blur_ramp", 10]],
                "print_fx": [["duotone", [20, 18, 16], [214, 206, 186]]],
                "title_face": "italic", "title_mode": "solid", "title_color": [214, 206, 186],
                "body_face": "serif", "body_weight": "Light", "caption_face": "serif_it",
                "shadow": "none", "halation": OFF, "slit_amp": 0, "grain": [0.05, 1.8]}),
    dict(slug="kawauchi", name="overexposed pastel", mood="가와우치: 과노출로 들뜬 파스텔, 하얀 지면, 가는 글자",
         technique="Rinko Kawauchi, Utatane (2001), pastel shift and square format",
         sources=["https://cphmag.com/rinko-kawauchis-world-of-wonders/"],
         quote="very deliberate, shifting everything towards pastel tones ... a light blueish tint",
         layer={"paper": [252, 252, 250], "ink": [90, 100, 108], "taupe": [214, 226, 228], "camel": [120, 140, 146],
                "saturation": 0.7, "tone": [[150, 170, 175], [255, 255, 252], 0.55],
                "hero_matte": [90, 255], "print_matte": [90, 255],
                "halation": [170, 30, [230, 245, 245], 0.6],
                "title_face": "inter", "title_weight": "Thin", "title_mode": "solid", "title_color": [150, 170, 175],
                "body_face": "sans", "body_weight": "Light", "caption_face": "serif_it",
                "shadow": "none", "slit_amp": 0, "grain": [0.01, 1.0]}),
    dict(slug="holzer-led", name="LED truism", mood="홀저: 알루미늄 판 위 앰버 LED, 카피가 전광판 문장처럼",
         technique="Jenny Holzer, Truisms on LED signs",
         sources=["https://en.wikipedia.org/wiki/Jenny_Holzer"],
         quote="LED signs have become her most visible medium",
         layer={"paper": [34, 36, 40], "ink": [255, 176, 40], "taupe": [70, 60, 44], "camel": [255, 176, 40],
                "light": [255, 176, 40], "note": [200, 140, 40], "saturation": 0.0,
                "hero_fx": [["duotone", [20, 14, 8], [255, 176, 40]], ["scanlines"]],
                "print_fx": [["duotone", [20, 14, 8], [255, 176, 40]], ["scanlines"]],
                "title_face": "inter", "title_weight": "Bold", "title_mode": "solid", "title_color": [255, 176, 40],
                "body_face": "sans", "body_weight": "Medium", "caption_face": "mono",
                "shadow": "none", "halation": [200, 8, [255, 190, 90], 0.5], "slit_amp": 0, "grain": [0.01, 1.0]}),
    dict(slug="paik-crt", name="TV cabinet", mood="백남준: 나무 TV 함 안의 CRT, 주사선과 RGB 번짐, 형광 빛",
         technique="Nam June Paik, The More, The Better (1988), 1,003 CRT monitors",
         sources=["https://en.wikipedia.org/wiki/The_More,_The_Better"],
         quote="adorned entirely with an impressive arrangement of 1,003 cathode ray tube (CRT) television monitors",
         layer={"paper": [120, 84, 56], "ink": [246, 236, 220], "taupe": [60, 40, 26], "camel": [190, 230, 255],
                "light": [210, 236, 255], "saturation": 1.3, "tone": [[10, 20, 30], [220, 245, 255], 0.2],
                "hero_fx": [["misregister", 3], ["scanlines"]], "print_fx": [["misregister", 2], ["scanlines"]],
                "halation": [160, 10, [180, 220, 255], 0.5],
                "title_face": "inter", "title_weight": "Black", "title_mode": "outline", "title_color": [190, 230, 255],
                "body_face": "sans", "body_weight": "Regular", "caption_face": "mono",
                "shadow": "none", "slit_amp": 0, "grain": [0.02, 1.0]}),
    dict(slug="xerox-zine", name="photocopy zine", mood="펑크 진: 복사기로 1비트가 된 사진, 토너 얼룩, 굵은 고딕",
         technique="Sniffin' Glue (1976), cut-and-paste, typewritten, photocopied fanzine",
         sources=["https://www.udiscovermusic.com/stories/40-years-ago-our-first-whiff-of-sniffin-glue"],
         quote="rudimentary cut-and-paste graphics, typewritten or felt-tipped text, and hastily photocopied end product",
         layer={"paper": [240, 238, 232], "ink": [12, 12, 12], "taupe": [12, 12, 12], "camel": [12, 12, 12],
                "hero_matte": [0, 255], "print_matte": [0, 255],
                "hero_fx": [["threshold", 0.48]], "print_fx": [["threshold", 0.5]],
                "title_face": "sans", "title_weight": "Black", "title_mode": "solid", "title_color": [12, 12, 12],
                "body_face": "sans", "body_weight": "Bold", "caption_face": "mono",
                "shadow": "threshold", "halation": OFF, "slit_amp": 0, "grain": [0.06, 1.2]}),
    dict(slug="rauschenberg-transfer", name="solvent transfer", mood="라우센버그: 용제로 옮긴 흐린 사진, 빗금 질감, 붉은 과슈",
         technique="Robert Rauschenberg, Thirty-Four Illustrations for Dante's Inferno (1958-60), solvent transfer",
         sources=["https://www.moma.org/collection/works/36730"],
         quote="transferring photographic reproductions from magazines or newspapers onto the drawing surface",
         layer={"paper": [248, 246, 240], "ink": [70, 64, 60], "taupe": [190, 50, 40], "camel": [190, 50, 40],
                "saturation": 0.5, "hero_matte": [110, 250], "print_matte": [110, 250],
                "hero_fx": [["dither", [96, 86, 80], 1], ["blur_ramp", 4]], "print_fx": [["dither", [96, 86, 80], 1]],
                "title_face": "italic", "title_mode": "outline", "title_color": [190, 50, 40],
                "body_face": "serif", "body_weight": "Regular", "caption_face": "serif_it",
                "shadow": "none", "halation": OFF, "slit_amp": 0, "grain": [0.02, 1.4]}),
    dict(slug="ecriture", name="écriture", mood="단색화 묘법: 한지에 스며든 듯 아주 옅은 사진, 흑연 회색, 반복과 시간",
         technique="Park Seo-Bo, Écriture (Myobop), pencil lines on wet layers of hanji",
         sources=["https://m.kukjegallery.com/exhibition/234"],
         quote="Through this repetitive action, the completed works manifest accumulated time",
         layer={"paper": [242, 239, 230], "ink": [80, 80, 82], "taupe": [200, 198, 192], "camel": [120, 120, 122],
                "saturation": 0.3, "hero_matte": [120, 240], "print_matte": [120, 240],
                "hero_fx": [["blur_ramp", 8]], "print_blur": 2.5,
                "title_face": "sans", "title_weight": "Thin", "title_mode": "outline", "title_color": [80, 80, 82],
                "body_face": "sans", "body_weight": "Light", "caption_face": "serif_it",
                "shadow": "none", "halation": OFF, "slit_amp": 0, "grain": [0.035, 2.2]}),
    dict(slug="sabattier", name="solarised", mood="사바티에: 현상 중 빛을 켠 사고, 밝고 어두움이 뒤집힌 은빛 윤곽",
         technique="Lee Miller / Man Ray, solarisation (Sabatier effect), Paris c.1929",
         sources=["https://www.leemillerresearchguide.com/articles/blog-post-title-four-a6392"],
         quote="Something crawled across my foot in the darkroom and I let out a yell and turned on the light",
         layer={"paper": [228, 230, 232], "ink": [24, 26, 30], "taupe": [140, 144, 150], "camel": [70, 74, 80],
                "saturation": 0.0, "hero_fx": [["solarize", 110], ["duotone", [16, 18, 22], [236, 238, 240]]],
                "print_fx": [["solarize", 120], ["duotone", [16, 18, 22], [236, 238, 240]]],
                "title_face": "inter", "title_weight": "Light", "title_mode": "outline", "title_color": [24, 26, 30],
                "body_face": "serif", "body_weight": "Regular", "caption_face": "mono",
                "shadow": "ruff", "halation": [200, 12, [240, 244, 250], 0.4], "slit_amp": 0, "grain": [0.02, 1.2]}),
    dict(slug="aerochrome", name="false colour", mood="에어로크롬: 적외선 필름처럼 올리브 재킷이 마젠타로 뒤집힌 낯선 색",
         technique="Richard Mosse, The Enclave (2013), Kodak Aerochrome infrared film",
         sources=["https://www.unsw.edu.au/newsroom/news/2014/03/infrared-film-captures-congo-war"],
         quote="rendering the Congolese rainforest as a surreal landscape of vivid magenta, pinks and reds",
         layer={"paper": [250, 236, 240], "ink": [60, 20, 40], "taupe": [220, 120, 160], "camel": [160, 40, 90],
                "saturation": 1.2, "tone": [[60, 10, 40], [255, 214, 230], 0.6],
                "hero_fx": [["duotone", [40, 6, 30], [255, 200, 220]]],
                "print_fx": [["duotone", [40, 6, 30], [255, 200, 220]]],
                "title_face": "serif", "title_weight": "Black", "title_mode": "solid", "title_color": [200, 30, 110],
                "body_face": "serif", "body_weight": "Regular", "caption_face": "mono",
                "shadow": "ruff", "halation": OFF, "slit_amp": 0, "grain": [0.02, 1.2]}),
]

# Ideas the levers cannot express. Kept as a list for the user; never sent while the structure is fixed.
STRUCTURE = [
    dict(name="Baldessari 가격표 점", idea="얼굴 자리에 원색 원형 점, 장소마다 점 색을 옷 톤에 맞춤",
         needs="사진 위 그래픽 오버레이(사진 픽셀은 그대로). 규칙 해석 필요",
         source="https://www.kcur.org/2013-03-12/for-john-baldessari-conceptual-art-means-serious-mischief",
         quote="In 1985, in a fit of pique, Baldessari covered the faces with colored dots."),
    dict(name="Hockney 조이너", idea="한 장면을 겹친 조각 수십 장으로 다시 모은 큐비즘 모자이크",
         needs="주인공 풀블리드 대신 조각 배치. 원본은 한 장이라 '한 장을 타일로 자른 근사'라고 밝혀야 함",
         source="https://www.h2g2.com/edited_entry/A520840",
         quote="a series of photographs taken from different viewpoints, arranged (overlapping) to form a single piece"),
    dict(name="Stezaker 스플라이스", idea="네 장소의 같은 사람을 반씩 잘라 이어 한 몸이 두 장소를 입게",
         needs="주인공 자리를 두 사진의 이음으로. 카피 '장소가 틀이라면, 옷은 그 틀을 채우는 조합'과 가장 직접 맞음",
         source="https://www.npg.org.uk/whatson/display/2019/john-stezaker-portrait",
         quote="cutting out, slicing and splicing images"),
    dict(name="Sophie Calle 기록", idea="흑백 액자 사진 + 타자 원고 패널, 날짜·장소 기록처럼",
         needs="세로 제목 대신 텍스트 패널",
         source="https://en.wikipedia.org/wiki/Sophie_Calle",
         quote="photographic work often includes panels of text of her own writing"),
    dict(name="Christopher Wool 스텐실", idea="거대한 검정 스텐실 MATCH. 를 줄 끊어 'MAT / CH.'",
         needs="제목이 오른쪽 면 전체, 프린트는 작게",
         source="https://en.wikipedia.org/wiki/Christopher_Wool",
         quote="paintings of large, black, stenciled letters on white canvases"),
    dict(name="조각보", idea="네 장소 사진을 조각으로 잘라 솔기로 이어 양면이 한 장의 조각보",
         needs="양면 전체를 조각 배치로",
         source="https://www.vam.ac.uk/articles/jogakbo-traditional-korean-patchwork",
         quote="the left-over fabrics were not discarded, but would be used to create a jogakbo"),
    dict(name="David Carson 레이건", idea="카피가 사진 위로 겹치고 자간이 극단으로 벌어지는 무그리드",
         needs="그리드 해제. 강도는 카피 한 벌은 반드시 정상 판독",
         source="https://www.aiga.org/membership-community/aiga-awards/2014-aiga-medalist-david-carson",
         quote="endlessly contorting type, layout and grid into new configurations"),
    dict(name="픽셀 소팅", idea="밝기 구간의 픽셀을 정렬해 흘러내리게",
         needs="(스스로 뺌) 겉보기가 댄디의 슬릿스캔 줄무늬와 같은 계열",
         source="https://log.fakewhale.xyz/kim-asendorf-from-pixel-to-paradigm/",
         quote="introduced over a decade ago and made open source in 2012"),
]

SIGNATURE = {"title_mode": "strip", "shadow": "soft_jpeg"}   # the dandy's own levers; a card may not use them


def lint(card: dict) -> list[str]:
    """The writer's own hygiene (not a grade): rules a card must keep before it is sent."""
    L, bad = card["layer"], []
    for k, v in SIGNATURE.items():
        if L.get(k, v) == v:
            bad.append(f"{k}={v} is the dandy's lever")
    if L.get("slit_amp", 40) != 0:
        bad.append("slit-scan left on")
    if not card.get("sources") or not card.get("quote"):
        bad.append("no checked source")
    return bad


def next_no(relay: str) -> int:
    nos = [int(m.group(1)) for d in os.listdir(relay) if (m := re.match(r"(\d{3})-", d))] if os.path.isdir(relay) else []
    return max(nos, default=-1) + 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--relay", default=RELAY)
    ap.add_argument("--list", action="store_true")
    a = ap.parse_args()
    sent = {m.group(1) for d in os.listdir(a.relay) if (m := re.match(r"\d{3}-(.+)$", d))} if os.path.isdir(a.relay) else set()
    n = next_no(a.relay)
    for c in CARDS:
        bad = lint(c)
        if a.list or bad or c["slug"] in sent:
            print(f"{'skip' if (bad or c['slug'] in sent) else '    '} {c['slug']:24s} {c['mood']}  {'; '.join(bad)}")
            continue
        d = os.path.join(a.relay, f"{n:03d}-{c['slug']}")
        os.makedirs(d, exist_ok=True)
        spec = {k: c[k] for k in ("name", "mood", "sources", "layer")}
        spec["technique"], spec["quote"] = c["technique"], c["quote"]
        with open(os.path.join(d, "spec.json"), "w", encoding="utf-8") as f:
            json.dump(spec, f, ensure_ascii=False, indent=1)
        print(f"sent {d}")
        n += 1


if __name__ == "__main__":
    main()
