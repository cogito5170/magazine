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
  * a mood redesigns the whole page (user, 2026-10-25: "지난 세션에서는 무드 바꾸면 다 바꿨는데"): every new
    card carries a `structure` block -- layout, title, photo placement -- not only colour and levers
  * the approved recipe goes into every kind (edas/mood/kinds/recipe.py; user: "과감함이나 낯설게하기도 없고 정제도
    안 되어 있고"): from round 3 on, a card names `defamiliarize` (one device) and `techniques` (2-3 approved
    palette techniques, e.g. halation, matte, JPEG shadow) at the top level of its spec
  * the user's top criteria (2026-10-25), the first filter for every card: 1. 익숙한 낯섦 (familiar, yet somewhere
    strange, so it reads as art) and 2. 과감한 안정 (bold and challenging, yet never uncomfortable or ugly). From
    round 3 a card states both in `familiar_strange` and `bold_stable`: what stays familiar, what is made strange,
    what is bold, and what keeps it stable and beautiful
  * each card names one art technique and a source that was opened and read in this session (`quote`)

Round 2 cards (STRUCTURE_CARDS) also change the layout; they carry a `structure` block for new editor functions.
"""
from __future__ import annotations

import argparse
import json
import os
import re

RELAY = "/mnt/project-files/mood-relay"
OFF = [255, 1, [255, 255, 255], 0.0]                        # halation with zero strength

CARDS = [
    dict(round=1, slug="cyanotype", name="cyanotype specimen", mood="청사진: 네 장소를 프러시안 블루 한 톤으로 맞춘 표본",
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
    dict(round=1, slug="kruger", name="red bar", mood="크루거: 흑백 사진 위 빨간 띠와 굵은 기울임 고딕, 카피가 선언처럼",
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
    dict(round=1, slug="provoke", name="are bure boke", mood="프로보크: 거칠고 흔들리고 초점 나간 흑백, 갱지",
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
    dict(round=1, slug="polke-raster", name="raster", mood="폴케: 신문 망점을 크게 키워 사진이 점으로 풀리는 지면",
         technique="Sigmar Polke, Rasterbilder (1960s), magnified newsprint dots",
         sources=["https://en.wikipedia.org/wiki/Sigmar_Polke"],
         quote="exploit the raster-dot technique of printing as a way as of subverting and bringing into question the apparent truth",
         layer={"paper": [232, 224, 200], "ink": [30, 28, 26], "taupe": [150, 140, 116], "camel": [90, 80, 64],
                "hero_fx": [["halftone", 14, [30, 28, 26]]], "print_fx": [["halftone", 7, [30, 28, 26]]],
                "title_face": "inter", "title_weight": "Bold", "title_mode": "outline", "title_color": [30, 28, 26],
                "body_face": "sans", "body_weight": "Regular", "caption_face": "mono",
                "shadow": "none", "halation": OFF, "slit_amp": 0, "grain": [0.02, 1.2]}),
    dict(round=1, slug="weingart-film", name="film montage", mood="바인가르트: 리스 필름을 겹친 듯 반전과 거친 망점, 시안 별색",
         technique="Wolfgang Weingart, layered film collages with rough halftone screens (Basel, 1970s-80s)",
         sources=["https://eyeondesign.aiga.org/museum-of-design-zurich-unveils-the-weingart-archive/"],
         quote="rough, fragmented dot screens ... The low resolution of the screens reveals the photo-mechanical process",
         layer={"paper": [246, 246, 244], "ink": [18, 18, 18], "taupe": [0, 120, 190], "camel": [0, 110, 176],
                "hero_fx": [["solarize", 150], ["halftone", 9, [0, 120, 190]]],
                "print_fx": [["solarize", 150], ["halftone", 5, [18, 18, 18]]],
                "title_face": "inter", "title_weight": "Thin", "title_mode": "outline", "title_color": [0, 120, 190],
                "body_face": "sans", "body_weight": "Light", "caption_face": "mono", "marks": True,
                "shadow": "threshold", "halation": OFF, "slit_amp": 0, "grain": [0.01, 1.0]}),
    dict(round=1, slug="tintype", name="wet plate", mood="습판: 어두운 금속판 위 은빛 단색, 가운데만 선명하고 가장자리는 흐름",
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
    dict(round=1, slug="kawauchi", name="overexposed pastel", mood="가와우치: 과노출로 들뜬 파스텔, 하얀 지면, 가는 글자",
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
    dict(round=1, slug="holzer-led", name="LED truism", mood="홀저: 알루미늄 판 위 앰버 LED, 카피가 전광판 문장처럼",
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
    dict(round=1, slug="paik-crt", name="TV cabinet", mood="백남준: 나무 TV 함 안의 CRT, 주사선과 RGB 번짐, 형광 빛",
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
    dict(round=1, slug="xerox-zine", name="photocopy zine", mood="펑크 진: 복사기로 1비트가 된 사진, 토너 얼룩, 굵은 고딕",
         technique="Sniffin' Glue (1976), cut-and-paste, typewritten, photocopied fanzine",
         sources=["https://www.udiscovermusic.com/stories/40-years-ago-our-first-whiff-of-sniffin-glue"],
         quote="rudimentary cut-and-paste graphics, typewritten or felt-tipped text, and hastily photocopied end product",
         layer={"paper": [240, 238, 232], "ink": [12, 12, 12], "taupe": [12, 12, 12], "camel": [12, 12, 12],
                "hero_matte": [0, 255], "print_matte": [0, 255],
                "hero_fx": [["threshold", 0.48]], "print_fx": [["threshold", 0.5]],
                "title_face": "sans", "title_weight": "Black", "title_mode": "solid", "title_color": [12, 12, 12],
                "body_face": "sans", "body_weight": "Bold", "caption_face": "mono",
                "shadow": "threshold", "halation": OFF, "slit_amp": 0, "grain": [0.06, 1.2]}),
    dict(round=1, slug="rauschenberg-transfer", name="solvent transfer", mood="라우센버그: 용제로 옮긴 흐린 사진, 빗금 질감, 붉은 과슈",
         technique="Robert Rauschenberg, Thirty-Four Illustrations for Dante's Inferno (1958-60), solvent transfer",
         sources=["https://www.moma.org/collection/works/36730"],
         quote="transferring photographic reproductions from magazines or newspapers onto the drawing surface",
         layer={"paper": [248, 246, 240], "ink": [70, 64, 60], "taupe": [190, 50, 40], "camel": [190, 50, 40],
                "saturation": 0.5, "hero_matte": [110, 250], "print_matte": [110, 250],
                "hero_fx": [["dither", [96, 86, 80], 1], ["blur_ramp", 4]], "print_fx": [["dither", [96, 86, 80], 1]],
                "title_face": "italic", "title_mode": "outline", "title_color": [190, 50, 40],
                "body_face": "serif", "body_weight": "Regular", "caption_face": "serif_it",
                "shadow": "none", "halation": OFF, "slit_amp": 0, "grain": [0.02, 1.4]}),
    dict(round=1, slug="ecriture", name="écriture", mood="단색화 묘법: 한지에 스며든 듯 아주 옅은 사진, 흑연 회색, 반복과 시간",
         technique="Park Seo-Bo, Écriture (Myobop), pencil lines on wet layers of hanji",
         sources=["https://m.kukjegallery.com/exhibition/234"],
         quote="Through this repetitive action, the completed works manifest accumulated time",
         layer={"paper": [242, 239, 230], "ink": [80, 80, 82], "taupe": [200, 198, 192], "camel": [120, 120, 122],
                "saturation": 0.3, "hero_matte": [120, 240], "print_matte": [120, 240],
                "hero_fx": [["blur_ramp", 8]], "print_blur": 2.5,
                "title_face": "sans", "title_weight": "Thin", "title_mode": "outline", "title_color": [80, 80, 82],
                "body_face": "sans", "body_weight": "Light", "caption_face": "serif_it",
                "shadow": "none", "halation": OFF, "slit_amp": 0, "grain": [0.035, 2.2]}),
    dict(round=1, slug="sabattier", name="solarised", mood="사바티에: 현상 중 빛을 켠 사고, 밝고 어두움이 뒤집힌 은빛 윤곽",
         technique="Lee Miller / Man Ray, solarisation (Sabatier effect), Paris c.1929",
         sources=["https://www.leemillerresearchguide.com/articles/blog-post-title-four-a6392"],
         quote="Something crawled across my foot in the darkroom and I let out a yell and turned on the light",
         layer={"paper": [228, 230, 232], "ink": [24, 26, 30], "taupe": [140, 144, 150], "camel": [70, 74, 80],
                "saturation": 0.0, "hero_fx": [["solarize", 110], ["duotone", [16, 18, 22], [236, 238, 240]]],
                "print_fx": [["solarize", 120], ["duotone", [16, 18, 22], [236, 238, 240]]],
                "title_face": "inter", "title_weight": "Light", "title_mode": "outline", "title_color": [24, 26, 30],
                "body_face": "serif", "body_weight": "Regular", "caption_face": "mono",
                "shadow": "ruff", "halation": [200, 12, [240, 244, 250], 0.4], "slit_amp": 0, "grain": [0.02, 1.2]}),
    dict(round=1, slug="aerochrome", name="false colour", mood="에어로크롬: 적외선 필름처럼 올리브 재킷이 마젠타로 뒤집힌 낯선 색",
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

# Round 2 (user, 2026-10-25: "레이아웃은 그대론데?"): the structure is open. These cards carry a `structure`
# block that the editor renders with NEW functions; the approved structure and its functions stay untouched.
# Geometry is in fractions of the 2000x1231 spread (gutter at x=0.5). Photo keys: night, park, shop, rock.
# Copy is used verbatim; nothing is added to it.
STRUCTURE_CARDS = [
    dict(round=2, slug="splice", name="splice", mood="스테자커: 같은 사람의 두 장소를 반씩 이어, 한 몸이 두 장소의 옷을 입는다",
         technique="John Stezaker, spliced found portraits (Marriage series)",
         sources=["https://www.npg.org.uk/whatson/display/2019/john-stezaker-portrait"],
         quote="cutting out, slicing and splicing images",
         structure={"kind": "splice", "pairs": [["night", "rock"], ["park", "shop"]], "cut": "vertical", "at": 0.5,
                    "align": "person box top and height", "placement": "one collage per page, centred, 0.32 of page width",
                    "mat": "wide museum mat around each collage", "title": "small caps serif under the left collage",
                    "body": "under the right collage, horizontal", "prints": 0},
         layer={"paper": [150, 150, 148], "ink": [24, 24, 24], "taupe": [120, 120, 118], "camel": [40, 40, 40],
                "title_face": "serif", "title_weight": "Regular", "title_mode": "solid", "title_color": [24, 24, 24],
                "body_face": "serif", "body_weight": "Regular", "caption_face": "serif_it", "shadow": "none",
                "halation": OFF, "slit_amp": 0}),
    dict(round=2, slug="jogakbo", name="jogakbo", mood="조각보: 네 장소 사진을 조각으로 잘라 솔기로 이은 한 장의 보자기",
         technique="jogakbo, Korean patchwork wrapping cloth of leftover scraps",
         sources=["https://www.vam.ac.uk/articles/jogakbo-traditional-korean-patchwork"],
         quote="the left-over fabrics were not discarded, but would be used to create a jogakbo",
         structure={"kind": "jogakbo", "photos": ["night", "park", "shop", "rock"], "pieces": [14, 22],
                    "piece_rule": "rectangles cut from the photos, each keeps the person box whole where it falls",
                    "seam": {"width": 3, "color": [248, 244, 232], "double": True}, "cover": "both pages edge to edge",
                    "title": "on one plain ramie piece", "body": "on one plain ramie piece, horizontal", "prints": 0},
         layer={"paper": [226, 214, 184], "ink": [40, 34, 28], "camel": [120, 90, 60],
                "title_face": "sans", "title_weight": "Medium", "title_mode": "solid", "title_color": [40, 34, 28],
                "body_face": "serif", "body_weight": "Regular", "caption_face": "serif_it", "shadow": "none",
                "halation": OFF, "slit_amp": 0}),
    dict(round=2, slug="joiner", name="joiner", mood="호크니 조이너: 한 장면을 겹친 조각 수십 장으로 다시 모은 시선의 모자이크",
         technique="David Hockney, joiners (photocollage, 1980s)",
         sources=["https://www.h2g2.com/edited_entry/A520840"],
         quote="a series of photographs taken from different viewpoints, arranged (overlapping) to form a single piece",
         structure={"kind": "joiner", "source": "night", "tiles": 36, "tile_rot_deg": [-6, 6], "overlap": 0.12,
                    "white_border": 8, "span": "across the gutter, 0.08-0.70 of spread width",
                    "honesty_note": "one source frame cut into tiles; Hockney shot each tile separately",
                    "title": "horizontal, small, top right", "body": "right page lower third", "prints": "park, shop, rock as three more small joiners"},
         layer={"paper": [58, 56, 54], "ink": [236, 232, 224], "camel": [200, 190, 170], "light": [236, 232, 224],
                "title_face": "inter", "title_weight": "Light", "title_mode": "solid", "title_color": [236, 232, 224],
                "body_face": "sans", "body_weight": "Light", "caption_face": "mono", "shadow": "none",
                "halation": OFF, "slit_amp": 0}),
    dict(round=2, slug="calle-panel", name="record", mood="소피 칼: 액자 속 흑백 사진과 타자 원고 패널, 기록처럼",
         technique="Sophie Calle, photographs paired with framed text panels",
         sources=["https://en.wikipedia.org/wiki/Sophie_Calle"],
         quote="photographic work often includes panels of text of her own writing",
         structure={"kind": "panel", "left": {"photo": "night", "bw": True, "frame": "black frame, white mat"},
                    "right": {"text_panel": "the copy only, verbatim, typewriter face, framed the same way"},
                    "title": "typed first line of the panel", "prints": "three small framed prints in a row under the panel"},
         layer={"paper": [246, 246, 244], "ink": [20, 20, 20], "camel": [80, 80, 80], "saturation": 0.0,
                "title_face": "sans", "title_weight": "Regular", "title_mode": "solid", "title_color": [20, 20, 20],
                "body_face": "sans", "body_weight": "Regular", "caption_face": "mono", "shadow": "none",
                "halation": OFF, "slit_amp": 0}),
    dict(round=2, slug="wool-stencil", name="stencil", mood="크리스토퍼 울: 오른쪽 면 전체를 덮는 검정 스텐실 MAT / CH.",
         technique="Christopher Wool, word paintings in black stencilled letters",
         sources=["https://en.wikipedia.org/wiki/Christopher_Wool"],
         quote="paintings of large, black, stenciled letters on white canvases",
         structure={"kind": "stencil_title", "title_lines": ["MAT", "CH."], "title_area": "whole right page, horizontal",
                    "stencil_bridges": True, "hero": "night, left page as approved but without slit-scan",
                    "prints": "three small prints in one row at the bottom of the right page", "body": "between title lines, small"},
         layer={"paper": [236, 234, 226], "ink": [14, 14, 14], "camel": [60, 60, 60],
                "title_face": "inter", "title_weight": "Black", "title_mode": "solid", "title_color": [14, 14, 14],
                "body_face": "sans", "body_weight": "Medium", "caption_face": "mono", "shadow": "none",
                "halation": OFF, "slit_amp": 0}),
    dict(round=2, slug="baldessari-dots", name="dots", mood="발데사리: 얼굴 자리에 원색 점, 점 색은 그 장소 옷의 톤",
         technique="John Baldessari, coloured dots over faces in found press photographs (1985-)",
         sources=["https://www.kcur.org/2013-03-12/for-john-baldessari-conceptual-art-means-serious-mischief"],
         quote="In 1985, in a fit of pique, Baldessari covered the faces with colored dots.",
         structure={"kind": "dots", "photos": ["night", "park", "shop", "rock"],
                    "layout": "four press prints of different sizes, slightly tilted, scattered across both pages",
                    "dot": {"on": "face = top 22% of the person box", "color": "mean of the outfit box, saturation x2"},
                    "rule_note": "a flat graphic over the photo; photo pixels unchanged. Needs the user's OK under the no-overpaint rule",
                    "title": "small grotesk, bottom left", "body": "small grotesk, bottom right"},
         layer={"paper": [244, 244, 240], "ink": [20, 20, 20], "camel": [80, 80, 80],
                "title_face": "inter", "title_weight": "Bold", "title_mode": "solid", "title_color": [20, 20, 20],
                "body_face": "sans", "body_weight": "Regular", "caption_face": "mono", "shadow": "none",
                "halation": OFF, "slit_amp": 0}),
    dict(round=2, slug="carson-nogrid", name="no grid", mood="데이비드 카슨: 그리드 없이 글과 사진이 겹치고 자간이 벌어진다",
         technique="David Carson, Ray Gun (1990s)",
         sources=["https://www.aiga.org/membership-community/aiga-awards/2014-aiga-medalist-david-carson"],
         quote="endlessly contorting type, layout and grid into new configurations",
         structure={"kind": "nogrid", "hero": "park, cropped to the person at 3x, bleeding over the gutter",
                    "title": "letters of MATCH. at five different sizes and baselines",
                    "body": "set once normally and readable; may overlap the photo edge only",
                    "prints": "night, shop, rock cropped to slivers, overlapping each other",
                    "intensity": "the copy must stay readable once (not 'unwatchable')"},
         layer={"paper": [250, 250, 250], "ink": [16, 16, 16], "camel": [230, 80, 30],
                "title_face": "inter", "title_weight": "Black", "title_mode": "solid", "title_color": [230, 80, 30],
                "body_face": "sans", "body_weight": "Regular", "caption_face": "mono", "shadow": "none",
                "halation": OFF, "slit_amp": 0}),
    dict(round=2, slug="kruger-bars", name="red bars", mood="크루거: 한 장면이 양면을 덮고, 제목과 카피가 빨간 띠로 가로지른다",
         technique="Barbara Kruger, black-and-white photographs with white-on-red Futura Bold Oblique",
         sources=["https://whitney.org/artists/2635"],
         quote="black-and-white photographs ... white-on-red Futura Bold Oblique or Helvetica Ultra Condensed",
         structure={"kind": "bars", "hero": "park, black and white, both pages edge to edge",
                    "bars": [{"text": "title", "y": 0.18}, {"text": "body line 1", "y": 0.64}, {"text": "body line 2", "y": 0.76}],
                    "bar_color": [204, 20, 30], "text_color": [255, 255, 255],
                    "prints": "night, shop, rock as three small insets with a red border, right page"},
         layer={"paper": [16, 16, 16], "ink": [255, 255, 255], "camel": [204, 20, 30], "saturation": 0.0,
                "title_face": "inter", "title_weight": "Black", "title_mode": "solid", "title_color": [255, 255, 255],
                "body_face": "sans", "body_weight": "Bold", "caption_face": "mono", "shadow": "none",
                "halation": OFF, "slit_amp": 0}),
]

# Round 3 (user: "넓혀", widen the family of the liked 022 red bars): black-and-white photograph, one loud colour,
# the copy set like a statement.  Composers written by the writer: edas/mood/kinds/{monochrome,intertitle,poster,
# diagonal}.py (shared pieces in _declare.py), each calling the approved recipe.
BW = {"saturation": 0.0, "shadow": "none", "slit_amp": 0, "title_face": "inter", "title_mode": "solid",
      "body_face": "sans", "body_weight": "Regular", "caption_face": "mono"}
DECLARE_CARDS = [
    dict(round=3, slug="klein-field", name="IKB field", mood="클라인: 한 면은 울트라마린뿐, 다른 면은 흑백 사진. 제목이 접지선에서 잘린다",
         technique="Yves Klein, International Klein Blue (IKB process registered 19 May 1960)",
         sources=["https://www.centrepompidou.fr/en/pompidou-plus/magazine/article/the-untold-story-of-the-international-klein-blue-ikb-of-yves-klein"],
         quote="The resin held the pigment in place without altering its brilliance (Rhodopas M); envelope Soleau no. 63471",
         structure={"kind": "monochrome", "field": [0, 47, 167]},
         defamiliarize="title cut by the gutter: white on the blue, blue on a white panel over the photograph",
         techniques=["Richter strip title", "slit-scan amp 40", "matte"],
         familiar_strange="익숙함: 흑백 패션 사진, 잡지 펼침면. 낯섦: 한 면이 통째로 아무것도 없는 파랑",
         bold_stable="과감함: 페이지 절반을 단색 하나로. 안정: 좌우 반반 대칭, 색은 파랑 하나",
         layer=dict(BW, paper=[0, 47, 167], ink=[246, 246, 244], camel=[246, 246, 244])),
    dict(round=3, slug="godard-cards", name="intertitles", mood="고다르: 검은 필름 리더 위에 제목을 두 장의 자막 카드로 끊는다. MAT 파랑, CH. 빨강",
         technique="Jean-Luc Godard, intertitles (Masculin féminin, Le Weekend)",
         sources=["https://walkerart.org/magazine/godards-intertitles2"],
         quote="Blue, white and red text is a common Godardian palette ... 'Analyse,' broken into two lines, serves as the chapter title",
         structure={"kind": "intertitle", "first": [40, 86, 230], "second": [226, 34, 40]},
         defamiliarize="the title broken across two intertitle cards, blue then red",
         techniques=["Richter strip title", "slit-scan amp 40", "matte", "misregister 3 px"][:3],
         familiar_strange="익숙함: 영화 스틸과 자막. 낯섦: 단어가 두 카드로 끊겨 장면 사이에 끼어든다",
         bold_stable="과감함: 검정 바탕에 원색 두 개. 안정: 가운데 정렬 한 축, 카드 리듬",
         layer=dict(BW, paper=[12, 12, 12], ink=[240, 238, 232], camel=[240, 238, 232])),
    dict(round=3, slug="yellow-poster", name="yellow poster", mood="게릴라 걸스: 노란 바탕에 흑백 인물, 큰 검정 제목, 작은 분홍 하나",
         technique="Guerrilla Girls, Do Women Have to Be Naked to Get into the Met. Museum? (1989)",
         sources=["https://smarthistory.org/guerrilla-girls-women-met-museum"],
         quote="loud black text on the loud yellow ... a pink element in the lower left corner",
         structure={"kind": "poster", "ground": [255, 212, 0]},
         defamiliarize="the title in two weights joined at a letter: Black | Thin",
         techniques=["Richter strip title", "slit-scan amp 40", "matte"],
         familiar_strange="익숙함: 거리 포스터, 흑백 인물. 낯섦: 패션 지면이 선언 포스터의 목소리로 말한다",
         bold_stable="과감함: 지면 전체가 노랑. 안정: 흑백 사진 한 장, 검정 글자, 정렬된 프린트 한 줄",
         layer=dict(BW, paper=[255, 212, 0], ink=[14, 14, 14], camel=[14, 14, 14])),
    dict(round=3, slug="rodchenko-wedge", name="red wedge", mood="로드첸코: 기울인 흑백 사진을 빨간 쐐기가 대각으로 가른다",
         technique="Alexander Rodchenko, diagonal compositions and odd angles; Lengiz poster (1924)",
         sources=["https://en.wikipedia.org/wiki/Alexander_Rodchenko"],
         quote="emphasised dynamic diagonal composition ... often shot his subjects from odd angles",
         structure={"kind": "diagonal", "wedge": [206, 28, 32], "angle": 8},
         defamiliarize="title weight stepped 100→900 inside the wedge",
         techniques=["Richter strip title", "matte", "misregister 3 px"],
         familiar_strange="익숙함: 흑백 패션 사진, 붉은 제목. 낯섦: 사진이 수평에서 8° 기울고 지면이 대각으로 갈라진다",
         bold_stable="과감함: 빨간 삼각형이 양면을 가로지른다. 안정: 모든 요소가 같은 축, 카피는 흰 띠 위에 정돈",
         layer=dict(BW, paper=[240, 238, 232], ink=[14, 14, 14], camel=[206, 28, 32])),
]

# Round 3 fixes after the judge (023 copy-fits, 024 bold/ΔE/layout, 026 panels-solid); the composers were fixed,
# 024 moves the still to the right page on a white leader with larger cards.
def _v2(slug, **kw):
    c = dict(next(x for x in DECLARE_CARDS if x["slug"] == slug))
    c.update(slug=slug + "-v2", **kw)
    return c


DECLARE_CARDS += [
    _v2("klein-field"),
    _v2("godard-cards", structure={"kind": "intertitle", "still": "right", "card_size": 330, "frame_h": 140,
                                   "copy_size": 21, "first": [40, 86, 230], "second": [226, 34, 40]},
        familiar_strange="익숙함: 영화 스틸과 자막. 낯섦: 단어가 두 장의 자막 카드로 끊겨 프레임 사이에 끼어든다",
        bold_stable="과감함: 지면 높이를 채우는 파랑·빨강 두 단어. 안정: 흰 리더, 가운데 정렬 한 축",
        layer=dict(BW, paper=[246, 246, 244], ink=[16, 16, 16], camel=[16, 16, 16])),
    _v2("rodchenko-wedge"),
]

DROPPED = {"pixel sort (Asendorf)": "looks like the dandy's slit-scan streaks"}

SIGNATURE = {"title_mode": "strip", "shadow": "soft_jpeg"}   # the dandy's own levers; a card may not use them


ROUND3 = True     # cards written from round 3 on must carry the recipe fields


def lint(card: dict) -> list[str]:
    """The writer's own hygiene (not a grade): rules a card must keep before it is sent."""
    L, bad = card["layer"], []
    if ROUND3 and card.get("round", 3) >= 3:
        if not card.get("defamiliarize"):
            bad.append("no defamiliarize device")
        if not 2 <= len(card.get("techniques", [])) <= 3:
            bad.append("needs 2-3 approved techniques")
        for k in ("familiar_strange", "bold_stable"):
            if not card.get(k):
                bad.append(f"no {k} (user's top criteria)")
        if not card.get("structure"):
            bad.append("no structure (a mood redesigns the whole page)")
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
    for c in CARDS + STRUCTURE_CARDS + DECLARE_CARDS:
        bad = lint(c)
        if a.list or bad or c["slug"] in sent:
            print(f"{'skip' if (bad or c['slug'] in sent) else '    '} {c['slug']:24s} {c['mood']}  {'; '.join(bad)}")
            continue
        d = os.path.join(a.relay, f"{n:03d}-{c['slug']}")
        os.makedirs(d, exist_ok=True)
        spec = {k: c[k] for k in ("name", "mood", "sources", "layer", "structure", "defamiliarize", "techniques", "familiar_strange", "bold_stable") if k in c}
        spec["technique"], spec["quote"] = c["technique"], c["quote"]
        with open(os.path.join(d, "spec.json"), "w", encoding="utf-8") as f:
            json.dump(spec, f, ensure_ascii=False, indent=1)
        print(f"sent {d}")
        n += 1


if __name__ == "__main__":
    main()
