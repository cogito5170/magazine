"""Art-directed mood treatments (instinct over documentation).

Rules for this round
* the four photographs are the only imagery; they may be cropped hard,
  enlarged and covered by a uniform film grain (recorded per photo);
  no colour grading, no retouching, no generated imagery;
* nothing analytic is printed on the page (no swatches, codes, labels);
* copy is verbatim.
The low resolution of the supplied screenshot makes every enlargement soft;
grain is used to make that softness read as texture.  Final production
needs the original photo files.
"""
from __future__ import annotations

import os

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from .variants import F, fnt, rgb8, width
from .photo_led import tracked

W, H, GUT = 2000, 1231, 1000


def cover(img: Image.Image, box_wh: tuple[int, int], focus=(0.5, 0.5)) -> tuple[Image.Image, dict]:
    """Crop to the target aspect around a focus point, then scale to fill."""
    tw, th = box_wh
    iw, ih = img.size
    a = tw / th
    if iw / ih > a:
        cw, ch = int(round(ih * a)), ih
    else:
        cw, ch = iw, int(round(iw / a))
    x0 = int(np.clip(focus[0] * iw - cw / 2, 0, iw - cw))
    y0 = int(np.clip(focus[1] * ih - ch / 2, 0, ih - ch))
    c = img.crop((x0, y0, x0 + cw, y0 + ch)).resize((tw, th), Image.LANCZOS)
    return c, {"source_window": (x0, y0, x0 + cw, y0 + ch), "scale": tw / cw,
               "area_retention": cw * ch / (iw * ih)}


def grain(img: Image.Image, amp: float, seed: int, size: float = 1.0) -> Image.Image:
    a = np.asarray(img.convert("RGB"), float) / 255
    rng = np.random.default_rng(seed)
    h, w = a.shape[:2]
    n = rng.normal(0, 1, (int(h / size) + 1, int(w / size) + 1))
    if size > 1:
        n = np.asarray(Image.fromarray(n.astype(np.float32), mode="F").resize((w, h), Image.BILINEAR))
    n = n[:h, :w]
    return Image.fromarray((np.clip(a + amp * n[..., None], 0, 1) * 255).astype("uint8"))


def scrim(page: Image.Image, box, strength: float = 0.55, direction: str = "up") -> Image.Image:
    """Soft dark gradient under text for legibility (a local darkening, recorded)."""
    a = np.asarray(page, float)
    x0, y0, x1, y1 = box
    h = y1 - y0
    t = np.linspace(0, 1, h)[:, None] if direction == "up" else np.linspace(1, 0, h)[:, None]
    a[y0:y1, x0:x1] *= (1 - strength * t ** 1.4)[..., None]
    return Image.fromarray(np.clip(a, 0, 255).astype("uint8"))


# ------------------------------------------------------------------ 1. NOCTURNE
def nocturne(crops, texts):
    rec = {}
    bg = (10, 11, 11)
    page = Image.new("RGB", (W, H), bg)
    left, info = cover(crops["night"], (GUT, H), focus=(0.47, 0.52))
    page.paste(left, (0, 0))
    rec["night"] = dict(info, placement="full bleed, left page")
    d = ImageDraw.Draw(page)
    # the word is almost the same black as the page: it is felt before it is read
    ft = fnt("black", 360)
    tracked(d, (GUT + 40, H - 330), texts["title"], ft, (24, 26, 26), -6)
    # three small lit 'windows' in the dark, on a falling diagonal
    for key, w_, xy in (("park", 300, (1620, 110)), ("shop", 104, (1150, 430)), ("rock", 230, (1450, 640))):
        im = crops[key]
        s = w_ / im.size[0]
        im2 = im.resize((w_, max(1, round(im.size[1] * s))), Image.LANCZOS)
        page.paste(im2, xy)
        rec[key] = {"scale": s, "box": (xy[0], xy[1], xy[0] + im2.size[0], xy[1] + im2.size[1])}
    soft = (150, 150, 146)
    tracked(d, (GUT + 150, 1080), texts["kicker"], fnt("light", 13), soft, 4.2)
    fk = fnt("ko", 17)
    tracked(d, (GUT + 150, 1112), texts["body_ko"][0], fk, soft, 0.6)
    tracked(d, (GUT + 150, 1142), texts["body_ko"][1], fk, soft, 0.6)
    tracked(d, (46, 44), texts["running_head"], fnt("light", 11), (205, 205, 200), 3)
    tracked(d, (W - 60, H - 52), texts["folio"], fnt("light", 11), soft, 2)
    page = grain(page, 0.035, 11, size=1.4)
    return page, {"name": "NOCTURNE / 밤", "idea": "the night portrait fills one page; the other three places "
                  "appear as small lit windows in the dark; the title is black on black, half-felt",
                  "photos": rec, "treatment": "enlargement (night x2.2), film grain on the whole spread"}


# ------------------------------------------------------------------ 2. LINEUP
def lineup(crops, texts):
    rec = {}
    page = Image.new("RGB", (W, H), (0, 0, 0))
    pw = W // 4
    focus = {"night": (0.43, 0.55), "park": (0.73, 0.5), "shop": (0.42, 0.5), "rock": (0.56, 0.45)}
    order = ["night", "park", "shop", "rock"]
    for i, k in enumerate(order):
        im, info = cover(crops[k], (pw - (2 if i < 3 else 0), H), focus=focus[k])
        page.paste(im, (i * pw, 0))
        rec[k] = dict(info, placement=f"panel {i + 1} of 4, full height")
    d = ImageDraw.Draw(page)
    white = (238, 236, 230)
    # one word per panel along the top edge, like a contact sheet slate
    words = ["FOUR", "PLACES,", "FOUR", "OUTFITS."]
    for i, wd in enumerate(words):
        tracked(d, (i * pw + 26, 30), wd, fnt("light", 14), white, 4)
    # the title crosses all four bodies at the same height: one word holding four people together
    ft = fnt("thin", 250)
    tw_ = width(texts["title"], ft, 30)
    tracked(d, ((W - tw_) / 2, 470), texts["title"], ft, white, 30)
    fk = fnt("ko", 18)
    page = scrim(page, (0, H - 200, 500, H), 0.5)
    d = ImageDraw.Draw(page)
    tracked(d, (26, H - 96), texts["body_ko"][0], fk, white, 0.6)
    tracked(d, (26, H - 64), texts["body_ko"][1], fk, white, 0.6)
    tracked(d, (W - 60, H - 64), texts["folio"], fnt("light", 12), white, 2)
    page = grain(page, 0.04, 21, size=1.6)
    return page, {"name": "LINEUP / 네 개의 몸", "idea": "four tall panels, one body per place, faces always hidden; "
                  "a single thin word runs through all four figures", "photos": rec,
                  "treatment": "hard vertical crops, enlargement up to ~3.4x, film grain"}


# ------------------------------------------------------------------ 3. WILD
def wild(crops, texts):
    rec = {}
    page, info = cover(crops["rock"], (W, H), focus=(0.5, 0.48))
    rec["rock"] = dict(info, placement="full bleed, whole spread")
    d = ImageDraw.Draw(page)
    bone = (236, 232, 222)
    # raw, oversized title pushed off the top-left edge
    ft = fnt("black", 520)
    tracked(d, (-48, -150), texts["title"].rstrip("."), ft, bone, -14)
    page = scrim(page, (0, H - 420, 1000, H), 0.62)
    d = ImageDraw.Draw(page)
    # the other three places as a narrow contact strip, cut into the rock
    x, y = 70, H - 300
    for k in ("night", "park", "shop"):
        im = crops[k]
        s = 210 / im.size[1]
        im2 = im.resize((max(1, round(im.size[0] * s)), 210), Image.LANCZOS)
        page.paste(im2, (x, y))
        rec[k] = {"scale": s, "box": (x, y, x + im2.size[0], y + 210)}
        x += im2.size[0] + 10
    fk = fnt("ko", 19)
    tracked(d, (70, H - 66), texts["body_ko"][0] + " " + texts["body_ko"][1], fk, bone, 0.6)
    tracked(d, (70, H - 340), texts["kicker"], fnt("bold", 14), bone, 4)
    tracked(d, (W - 66, H - 66), texts["folio"], fnt("bold", 13), bone, 2)
    page = grain(page, 0.055, 31, size=1.8)
    return page, {"name": "WILD / 야성", "scrim": "bottom-left dark gradient under the copy", "idea": "the crouching figure on black volcanic rock becomes the whole "
                  "spread; an oversized title bleeds off the edge; the other places survive as a contact strip",
                  "photos": rec, "treatment": "enlargement x3.5 (very soft), heavy grain"}


# ------------------------------------------------------------------ 4. FABRIC
def fabric(crops, texts, photos):
    """Only the garments: each outfit region enlarged until it becomes a field of colour and texture."""
    rec = {}
    page = Image.new("RGB", (W, H), (0, 0, 0))
    pw = W // 4
    src_boxes = {p.key: p for p in photos}
    for i, k in enumerate(["night", "park", "shop", "rock"]):
        p = src_boxes[k]
        ox0, oy0, ox1, oy1 = p.outfit
        cx0, cy0, _, _ = p.crop
        # widen the garment sample window inside the clean crop, keeping faces out
        px0, py0, px1, py1 = p.person
        win = (max(px0, cx0) - cx0, max(oy0 - 40, cy0) - cy0, min(px1, p.crop[2]) - cx0, p.crop[3] - cy0)
        cw_, ch_ = crops[k].size
        win = (max(0, win[0]), max(0, win[1]), min(cw_, win[2]), min(ch_, win[3]))   # stay inside the photo
        g = crops[k].crop(win)
        im, info = cover(g, (pw - (2 if i < 3 else 0), H), focus=(0.5, 0.5))
        page.paste(im, (i * pw, 0))
        rec[k] = dict(info, garment_window=win)
    d = ImageDraw.Draw(page)
    white = (240, 238, 232)
    ft = fnt("light", 15)
    for i, wd in enumerate(["NIGHT", "DUSK", "DAY", "SEA"]):
        tracked(d, (i * pw + 26, 30), wd, ft, white, 5)
    page = scrim(page, (1500, H - 210, W, H), 0.5)
    d = ImageDraw.Draw(page)
    tracked(d, (1526, H - 150), texts["title"], fnt("thin", 46), white, 8)
    fk = fnt("ko", 15)
    tracked(d, (1526, H - 88), texts["body_ko"][0], fk, white, 0.5)
    tracked(d, (1526, H - 62), texts["body_ko"][1], fk, white, 0.5)
    page = grain(page, 0.05, 41, size=2.0)
    return page, {"name": "FABRIC / 결", "idea": "no faces, no places: only the four garments, enlarged into fields "
                  "of colour and texture; the outfit fills the frame", "photos": rec,
                  "treatment": "garment windows enlarged ~2–5x (deliberately soft), grain, one corner scrim"}


CONCEPTS = {"1_nocturne": nocturne, "2_lineup": lineup, "3_wild": wild, "4_fabric": fabric}


def render(src_path, photos, texts, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    srcim = Image.open(src_path).convert("RGB")
    inset = 3                                   # avoid border pixels of the source spread (pink edge)
    crops = {p.key: srcim.crop((p.crop[0] + inset, p.crop[1] + inset, p.crop[2] - inset, p.crop[3] - inset))
             for p in photos}
    specs = {}
    for k, fn in CONCEPTS.items():
        page, spec = fn(crops, texts, photos) if k == "4_fabric" else fn(crops, texts)
        path = os.path.join(out_dir, f"{k}.png")
        page.save(path, optimize=True)
        page.save(os.path.join(out_dir, f"{k}.pdf"), "PDF", resolution=144.0)
        spec["file"] = path
        specs[k] = spec
    return specs
