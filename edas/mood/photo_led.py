"""Photo-led tonal redesign of a spread ("the photographs set the mood").

Rules of this method
* photographs are kept: only rectangular crops, uniform scaling (no
  distortion, no colour change, no inpainting); crops avoid any overlay;
* every colour on the page is sampled from the photographs (paper from the
  lightest outfit tone, ink from the darkest), so graphics never out-shout
  the images;
* the concept text is kept verbatim; the 'match' idea is made visible as
  place-tone / outfit-tone swatch pairs measured from each photo;
* all measurements and choices are written to a spec JSON with their
  evidence type.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Optional

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from ..mathcore.color import contrast_ratio, dominant_colors, hsv_saturation, relative_luminance, rgb_to_lab, ciede2000

F = {
    "thin": "/usr/share/fonts/opentype/inter/InterDisplay-Thin.otf",
    "xlight": "/usr/share/fonts/opentype/inter/InterDisplay-ExtraLight.otf",
    "light": "/usr/share/fonts/opentype/inter/InterDisplay-Light.otf",
    "regular": "/usr/share/fonts/opentype/inter/InterDisplay-Regular.otf",
    "ko": "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
}


def font(k, s):
    return ImageFont.truetype(F[k], size=s, index=0)


def tracked(d, xy, text, f, fill, tr=0.0):
    x, y = xy
    for ch in text:
        d.text((x, y), ch, font=f, fill=fill)
        x += f.getlength(ch) + tr
    return x


def width(text, f, tr=0.0):
    return sum(f.getlength(c) + tr for c in text) - tr


@dataclass
class Photo:
    key: str
    crop: tuple[int, int, int, int]          # clean crop in source coordinates
    outfit: tuple[int, int, int, int]        # garment sample rect (source coordinates)
    person: tuple[int, int, int, int]        # person bbox (excluded from place tone)
    label: str


def lab_hex(rgb):
    return "#%02x%02x%02x" % tuple(int(round(v * 255)) for v in rgb)


def sample_tones(src: np.ndarray, p: Photo) -> dict:
    x0, y0, x1, y1 = p.outfit
    outfit = np.median(src[y0:y1, x0:x1].reshape(-1, 3), axis=0)
    cx0, cy0, cx1, cy1 = p.crop
    region = src[cy0:cy1, cx0:cx1].copy()
    m = np.ones(region.shape[:2], bool)
    px0, py0, px1, py1 = p.person
    m[max(0, py0 - cy0):max(0, py1 - cy0), max(0, px0 - cx0):max(0, px1 - cx0)] = False
    doms = dominant_colors(region, k=6, bins=6, mask=m)
    ol = rgb_to_lab(outfit[None])[0]
    place = next((d for d in doms if float(ciede2000(np.array(d["lab"]), ol)) > 10), doms[0])
    return {"outfit_rgb": outfit.tolist(), "outfit_hex": lab_hex(outfit), "place_rgb": place["rgb"],
            "place_hex": place["hex"], "place_share": place["share"],
            "delta_e00_place_outfit": float(ciede2000(np.array(place["lab"]), ol))}


def compose(src_path: str, photos: list[Photo], texts: dict, out_dir: str, size=(2000, 1231)) -> dict:
    os.makedirs(out_dir, exist_ok=True)
    srcim = Image.open(src_path).convert("RGB")
    src = np.asarray(srcim, float) / 255.0
    tones = {p.key: sample_tones(src, p) for p in photos}
    # palette from the photos: paper = lightest outfit tone lifted to L*≈94; ink = darkest outfit tone
    outs = sorted(photos, key=lambda p: float(relative_luminance(np.array(tones[p.key]["outfit_rgb"]))))
    light = np.array(tones[outs[-1].key]["outfit_rgb"])
    dark = np.array(tones[outs[0].key]["outfit_rgb"])
    paper = light + (1 - light) * 0.80
    ink = dark * 0.85
    soft = ink + (paper - ink) * 0.45
    if contrast_ratio(float(relative_luminance(soft)), float(relative_luminance(paper))) < 4.5:
        soft = ink + (paper - ink) * 0.30
    W, H = size
    rng = np.random.default_rng(3)
    grain = rng.normal(0, 0.006, (size[1], size[0]))[..., None]
    page = Image.fromarray((np.clip(paper[None, None, :] + grain, 0, 1) * 255).astype("uint8"))
    d = ImageDraw.Draw(page)
    INK = tuple(int(v * 255) for v in ink)
    SOFT = tuple(int(v * 255) for v in soft)
    gut = W // 2
    M = 84                                          # outer margin
    top = 150
    crops = {p.key: srcim.crop(p.crop) for p in photos}

    def place(img, x, y, w=None, h=None):
        iw, ih = img.size
        s = min((w or iw) / iw, (h or ih) / ih, 1.0)       # never upscale the source photographs
        im2 = img.resize((max(1, round(iw * s)), max(1, round(ih * s))), Image.LANCZOS) if s < 1 else img
        page.paste(im2, (int(x), int(y)))
        return (int(x), int(y), int(x) + im2.size[0], int(y) + im2.size[1]), s

    boxes, scales = {}, {}
    # left page: night portrait + concept text
    b, s = place(crops["night"], M, top, h=H - top - 230)
    boxes["night"], scales["night"] = b, s
    # right page: park on top, shop + rock below, sharing one content width (no upscaling)
    xr = gut + 70
    sh, rk = crops["shop"], crops["rock"]
    ar = sh.size[0] / sh.size[1] + rk.size[0] / rk.size[1]
    cw_max = W - gut - M - 70
    h_row = min(sh.size[1], rk.size[1], int((cw_max - 28) / ar))
    cw = int(round(h_row * ar)) + 28
    b, s = place(crops["park"], xr, top, w=cw)
    boxes["park"], scales["park"] = b, s
    y2 = max(b[3] + 64, boxes["night"][3] - min(sh.size[1], rk.size[1], h_row))   # align bottoms with the left page
    b, s = place(sh, xr, y2, h=h_row)
    boxes["shop"], scales["shop"] = b, s
    b, s = place(rk, boxes["shop"][2] + 28, y2, h=h_row)
    boxes["rock"], scales["rock"] = b, s

    # running head + folio
    tracked(d, (M, 78), texts["running_head"], font("light", 15), SOFT, 3.2)
    tracked(d, (W - M - width(texts["folio"], font("light", 15), 3), H - 78), texts["folio"], font("light", 15), SOFT, 3)
    # title and concept on the left page, right column (kept clear of the gutter)
    tx = boxes["night"][2] + 60
    limit = gut - 72
    tsize = 104
    while width(texts["title"], font("xlight", tsize), 2) > limit - tx and tsize > 40:
        tsize -= 2
    tracked(d, (tx - 5, top - 20), texts["title"], font("xlight", tsize), INK, 2)
    y = top + tsize + 30
    tracked(d, (tx, y), "PLACE", font("light", 12), SOFT, 2.6)
    tracked(d, (tx + 96, y), "OUTFIT", font("light", 12), SOFT, 2.6)
    d.rectangle([tx, y + 24, tx + 16, y + 40], fill=SOFT)
    d.rectangle([tx + 96, y + 24, tx + 112, y + 40], fill=tuple(int(v * 255) for v in ink + (paper - ink) * 0.7))
    tracked(d, (tx, y + 52), "각 사진 아래 두 색은 사진에서 측정한 장소의 톤과 옷의 톤", font("ko", 12), SOFT, 0.3)
    tracked(d, (tx + 24, y + 24), "장소의 톤", font("ko", 13), SOFT, 0.5)
    tracked(d, (tx + 120, y + 24), "옷의 톤", font("ko", 13), SOFT, 0.5)
    fk = font("ko", 19)
    lines = []
    for line in texts["body_ko"]:                     # verbatim text; only line breaks adapt to the measure
        if width(line, fk, 0.6) > limit - tx and ", " in line:    # prefer a break at the comma
            head, tail = line.split(", ", 1)
            lines += [head + ",", tail]
            continue
        cur = ""
        for word in line.split(" "):
            cand = (cur + " " + word).strip()
            if width(cand, fk, 0.6) > limit - tx and cur:
                lines.append(cur)
                cur = word
            else:
                cur = cand
        lines.append(cur)
    yb = boxes["night"][3] - len(lines) * 36 + 6
    tracked(d, (tx, yb - 56), texts["kicker"], font("light", 16), INK, 3.2)
    for i, line in enumerate(lines):
        tracked(d, (tx, yb + i * 36), line, fk, INK, 0.6)

    # captions: number + place/outfit swatch pair, measured from the photo
    def caption(key, n):
        x0, y0, x1, y1 = boxes[key]
        t = tones[key]
        cy = y1 + 16
        tracked(d, (x0, cy + 1), f"{n:02d}", font("light", 14), INK, 2)
        sx = x0 + 44
        for j, c in enumerate((t["place_rgb"], t["outfit_rgb"])):
            col = tuple(int(v * 255) for v in c)
            d.rectangle([sx + j * 24, cy + 2, sx + j * 24 + 16, cy + 18], fill=col)
        tracked(d, (x0, cy + 28), f"{t['place_hex'].upper()} · {t['outfit_hex'].upper()}", font("light", 11), SOFT, 1.2)

    for n, key in enumerate(["night", "park", "shop", "rock"], 1):
        caption(key, n)
    # gutter shadow hint (print spread)
    g = np.asarray(page, float)
    xs = np.arange(W)
    shade = 1 - 0.035 * np.exp(-((xs - gut) / 18.0) ** 2)
    g = g * shade[None, :, None]
    page = Image.fromarray(np.clip(g, 0, 255).astype("uint8"))
    out_png = os.path.join(out_dir, "match_redesign.png")
    page.save(out_png, optimize=True)
    page.save(os.path.join(out_dir, "match_redesign.pdf"), "PDF", resolution=144.0)
    spec = {
        "method": "photo-led tonal match",
        "photos": {p.key: {"crop_source_px": p.crop, "placed_box_px": boxes[p.key], "scale": scales[p.key],
                           "upscaled": scales[p.key] > 1.0, "label": p.label, **tones[p.key]} for p in photos},
        "palette": {"paper": lab_hex(paper), "ink": lab_hex(ink), "soft_ink": lab_hex(soft),
                    "rule": "paper = lightest outfit tone lifted 80% to white; ink = darkest outfit tone x0.85"},
        "contrast": {"ink_on_paper": contrast_ratio(float(relative_luminance(ink)), float(relative_luminance(paper))),
                     "soft_on_paper": contrast_ratio(float(relative_luminance(soft)), float(relative_luminance(paper)))},
        "texts_verbatim": texts,
        "files": {"png": out_png},
    }
    return spec
