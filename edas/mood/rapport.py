"""'WHERE PEOPLE STOP ?' — the rapport mood (라포).

Rapport is read through Tickle-Degnen & Rosenthal (1990): mutual attentiveness, positivity and
coordination.  Those components describe people with each other.  Carrying them over to a page is a
design analogy and an untested hypothesis:
  attentiveness → each person who stopped stays sharp while the moving world around them is drawn out;
  positivity    → warm light: cream paper, warm-brown ink, halation, a terracotta accent taken from the
                  hue of the source's own labels;
  coordination  → every person's centre sits on one shared eye line across the spread, and the six photos
                  stand shoulder to shoulder, overlapping at close (personal, after Hall 1966) distance.
The contemporary-art methods carry over from the MATCH final: Richter's divided/mirrored/repeated stripes
fill the title (taken from the smoothie stall's light), and the source is declared a poor image (Steyerl).
"""
from __future__ import annotations

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from .artdirect import grain
from .contemporary import halation, richter_strip, serif_kr
from .defamiliar import text_mask
from .photo_led import tracked
from .variants import fnt, width

W, H, M = 2000, 1123, 56
PAPER, INK, ACCENT, SOFT = (239, 231, 217), (70, 52, 42), (166, 98, 64), (150, 132, 116)
EYE_LINE = 590


def motion_outside(img: Image.Image, box, radius: int, feather: int = 8) -> Image.Image:
    """Horizontal motion blur everywhere except inside `box` (the person who stopped)."""
    a = np.asarray(img, float)
    pad = np.pad(a, ((0, 0), (radius, radius), (0, 0)), mode="edge")
    cs = np.cumsum(pad, axis=1)
    cs = np.concatenate([np.zeros_like(cs[:, :1]), cs], axis=1)
    blur = (cs[:, 2 * radius + 1:] - cs[:, :-2 * radius - 1]) / (2 * radius + 1)
    mask = Image.new("L", img.size, 0)
    ImageDraw.Draw(mask).rectangle(box, fill=255)
    m = np.asarray(mask.filter(ImageFilter.GaussianBlur(feather)), float)[..., None] / 255
    return Image.fromarray(np.clip(a * m + blur * (1 - m), 0, 255).astype("uint8"))


def warm_matte(img: Image.Image, floor=(64, 46, 36), ceil=(250, 242, 228)) -> Image.Image:
    a = np.asarray(img, float) / 255
    lo, hi = np.array(floor, float), np.array(ceil, float)
    return Image.fromarray((lo + a * (hi - lo)).astype("uint8"))


def prepare(src: Image.Image, cell, crop_top: int, cell_w: int, cell_h: int):
    cx, cy, bx0, by0, bx1, by1 = cell
    photo = src.crop((cx + 1, cy + crop_top, cx + cell_w - 1, cy + cell_h - 1))
    box = (bx0 - 1, max(0, by0 - crop_top), bx1 - 1, by1 - crop_top)
    return photo, box


def rapport_spread(src: Image.Image, cells: dict, texts: dict, crop_top=22, cell_w=218, cell_h=194):
    page = Image.new("RGB", (W, H), PAPER)
    rec = {}
    items = []
    for k, cell in cells.items():
        photo, box = prepare(src, cell, crop_top, cell_w, cell_h)
        s = float(np.clip(170 / (box[3] - box[1]), 1.6, 2.4))
        im = photo.resize((round(photo.size[0] * s), round(photo.size[1] * s)), Image.LANCZOS)
        b = tuple(round(v * s) for v in box)
        im = motion_outside(im, b, radius=int(6 * s))
        im = warm_matte(halation(im, threshold=185, radius=14, tint=(255, 200, 150), strength=0.4))
        items.append((k, im, b, s, photo.size))
    # coordination: the person centres are spaced evenly along one eye line; each photo hangs from its person
    centres = np.linspace(190, W - 240, len(items))
    for (k, im, b, s, psize), cxp in zip(items, centres):
        cyc = (b[1] + b[3]) / 2
        x = cxp - (b[0] + b[2]) / 2
        y = int(EYE_LINE - cyc)
        sh = Image.new("RGBA", (im.size[0] + 80, im.size[1] + 80), (0, 0, 0, 0))
        ImageDraw.Draw(sh).rectangle([40 + 10, 40 + 16, 40 + im.size[0] + 10, 40 + im.size[1] + 16],
                                     fill=INK + (110,))
        sh = sh.filter(ImageFilter.GaussianBlur(16))
        page.paste(sh, (int(x) - 40, y - 40), sh)
        page.paste(im, (int(x), y))
        rec[k] = {"scale": round(s, 2), "box_on_page": (int(x) + b[0], y + b[1], int(x) + b[2], y + b[3]),
                  "photo_on_page": (int(x), y, int(x) + im.size[0], y + im.size[1]), "source_px": psize}
    d = ImageDraw.Draw(page)
    # the shared eye line, marked only at the page edges
    for x0 in (14, W - 44):
        d.line([(x0, EYE_LINE), (x0 + 30, EYE_LINE)], fill=ACCENT, width=2)
    # title: the stall's light, divided, mirrored, repeated, inside a serif
    p05 = np.asarray(src.crop((cells["05"][0] + 1, cells["05"][1] + crop_top, cells["05"][0] + cell_w - 1,
                               cells["05"][1] + cell_h - 1))).astype(float)
    cx = int(np.argmax(p05.mean(axis=2).std(axis=0)))
    col = 0.62 * p05[:, cx, :] + 0.38 * np.array(INK, float)
    ft = serif_kr("SemiBold", 104)
    tw = int(width(texts["title"], ft, 2)) + 20
    m = text_mask((tw, 150), texts["title"], ft, (0, -18), 2)
    page.paste(richter_strip(col, tw, 150, stages=5), (M - 4, 78), m)
    d = ImageDraw.Draw(page)
    tracked(d, (M, 56), texts["n51"], fnt("serif_it", 20), ACCENT, 1)
    # section labels sit above their three photographs
    lab = serif_kr("Medium", 20)
    v0, s0 = rec["01"]["photo_on_page"], rec["04"]["photo_on_page"]
    vx = max(M, v0[0] + 12)
    tracked(d, (vx, v0[1] - 64), texts["n52"], fnt("serif_it", 17), ACCENT, 1)
    tracked(d, (vx, v0[1] - 40), texts["void"], lab, INK, 3)
    s_top = min(rec[k]["photo_on_page"][1] for k in ("04", "05", "06"))
    tracked(d, (s0[0] + 12, s_top - 64), texts["n53"], fnt("serif_it", 17), ACCENT, 1)
    tracked(d, (s0[0] + 12, s_top - 40), texts["sense"], lab, INK, 3)
    # WHY?, under the second half, in a warm light serif
    bx, by = 1300, 800
    tracked(d, (bx, by), texts["n54"], fnt("serif_it", 17), ACCENT, 1)
    tracked(d, (bx, by + 24), texts["why"], serif_kr("Medium", 26), INK, 2)
    fb = serif_kr("Light", 19)
    lines, cur = [], ""
    for wd in texts["body"].split(" "):
        cand = (cur + " " + wd).strip()
        if fb.getlength(cand) > W - M - bx and cur:
            lines.append(cur)
            cur = wd
        else:
            cur = cand
    lines.append(cur)
    y = by + 74
    for ln in lines:
        d.text((bx, y), ln, font=fb, fill=INK)
        y += 32
    # NEXT, as a pointer at the foot
    tracked(d, (W - M - 130, H - 62), f"{texts['n55']}  {texts['next']} →", fnt("serif_it", 17), ACCENT, 1)
    # the original's foot rule with crosses
    yy = H - 30
    d.line([(M, yy), (W - M, yy)], fill=SOFT, width=1)
    for xx in (M, W // 2, W - M):
        d.line([(xx - 8, yy), (xx + 8, yy)], fill=INK, width=1)
        d.line([(xx, yy - 8), (xx, yy + 8)], fill=INK, width=1)
    sizes = sorted({r["source_px"] for r in rec.values()})
    tracked(d, (M, H - 62), f"Six photographs of about {sizes[0][0]} × {sizes[0][1]} px, enlarged "
            f"×{min(r['scale'] for r in rec.values()):.1f}–{max(r['scale'] for r in rec.values()):.1f}. "
            "Whoever stopped stays sharp; whatever moved on is drawn out.", fnt("serif_it", 16), SOFT, 0.3)
    return grain(page, 0.02, 31, size=1.4), {
        "name": "WHERE PEOPLE STOP ? — rapport",
        "mood_intent": "rapport (라포): attentiveness, positivity, coordination — a design analogy, untested",
        "eye_line_y": EYE_LINE, "photos": rec, "title_strip_column_05": cx,
        "treatments": ["motion blur outside each dashed person box (radius 6×scale px)",
                       "scale = 170 px / person-box height, clipped to 1.6–2.4",
                       "halation >185, warm tint", "warm matte (floor #402E24, ceiling #FAF2E4)",
                       "label rows cropped (top 22 px of each cell)"],
        "anchors": ["Tickle-Degnen & Rosenthal 1990", "Hall 1966 (proxemics)", "Richter, Patterns 2012",
                    "Steyerl 2009"],
        "copy_note": "the (5.5) NEXT body in the source duplicates the (5.4) WHY? body; set once"}
