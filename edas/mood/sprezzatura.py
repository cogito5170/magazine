"""MATCH cover + spread in a new mood: 스프레차투라 (sprezzatura), effortless, studied ease.

Mood source (checked this session): Baldassare Castiglione, *The Book of the Courtier* (1528), as quoted from
the Penguin edition (1967, pp. 66–68) at https://courses.washington.edu/hsteu401/Courtier%20sprezzatura.htm:
a "certain nonchalance" that "conceals all artistry" and "makes whatever one says or does seem uncontrived
and effortless"; avoid "affectation"; "true art is what does not seem to be art".
Contemporary-art method (checked): Wolfgang Tillmans tapes unframed prints of varied size and orientation
directly onto the wall as a "constellated installation", to "peel away any sense of artifice"
(https://unframed.lacma.org/node/2835).

Components → page devices (a design analogy, untested):
  nonchalance        → placement: unframed prints taped to the page, varied sizes, two of them a degree off
                       true, a few edges sharing a line, the rest loose;
  concealed artistry → treatment: the series' methods at their approved strengths, kept quiet: the Richter
                       title stays low in contrast, the JPEG shadow is printed in the source's own blue;
  no affectation     → type: plain Pretendard Light for the Korean copy, Caladea Italic for small notes;
  palette            → sampled from the source: its paper, its blue panel, its floor, the model's black
                       sleeve lifted one step.
Series DNA and intensity are unchanged: Richter strip title (`contemporary.richter_strip`), source size and
enlargement on the page, matte/halation/soft_jpeg at the values `nocturne_dandy` uses.  No approved
function is modified.  Photographs are cropped, scaled and rotated by ≤1.2° only.
"""
from __future__ import annotations

import numpy as np
from PIL import Image, ImageDraw

from .artdirect import grain
from .contemporary import halation, matte, richter_strip, serif_kr, soft_jpeg
from .defamiliar import text_mask
from .final import kr
from .photo_led import tracked
from .variants import fnt, width


def palette(src_paper, src_blue, src_floor, src_sleeve):
    lift = lambda c, t: tuple(int(round(v + (255 - v) * t)) for v in c)      # noqa: E731
    return {"paper": src_paper, "ink": lift(src_sleeve, 0.14), "shadow": src_blue,
            "note": (104, 116, 134), "tape": src_floor}


def taped(page, img, xy, angle, P, shadow=True, tape=((0.18, -1), (0.82, 1))):
    """Paste an unframed print at xy (top-left before rotation), turned by `angle`°, over its soft JPEG shadow
    in the source blue (×1.16 at −30, +24, as nocturne_dandy), with strips of paper tape at the top edge."""
    w, h = img.size
    if shadow:
        sh = soft_jpeg(img.resize((int(w * 1.16), int(h * 1.16)), Image.LANCZOS), P["paper"], P["shadow"])
        sh = sh.convert("RGBA").rotate(angle, resample=Image.BICUBIC, expand=True)
        page.paste(sh, (xy[0] - 30, xy[1] + 24), sh)
    im = img.convert("RGBA").rotate(angle, resample=Image.BICUBIC, expand=True)
    page.paste(im, xy, im)
    ov = Image.new("RGBA", page.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    cx0, cy0 = xy[0] + im.size[0] / 2, xy[1] + im.size[1] / 2
    t = np.deg2rad(-angle)
    for fx, tilt in tape:
        px, py = (fx - 0.5) * w, -h / 2
        x = cx0 + px * np.cos(t) - py * np.sin(t)
        y = cy0 + px * np.sin(t) + py * np.cos(t)
        strip = Image.new("RGBA", (74, 24), P["tape"] + (120,))
        strip = strip.rotate(angle + 6 * tilt, resample=Image.BICUBIC, expand=True)
        ov.alpha_composite(strip, (int(x - strip.size[0] / 2), int(y - strip.size[1] / 2)))
    page.paste(Image.alpha_composite(page.convert("RGBA"), ov).convert("RGB"))
    return im.size


def _title(page, src_img, col_frac, text, size, xy, P, mix=0.55):
    a = np.asarray(src_img, float)
    col = a[int(a.shape[0] * col_frac[1]):int(a.shape[0] * col_frac[2]), int(a.shape[1] * col_frac[0]), :]
    col = mix * col + (1 - mix) * np.array(P["paper"], float) * 0.86
    ft = serif_kr("SemiBold", size)
    tw = int(width(text, ft, size * 0.04)) + 30
    th = int(size * 1.2)
    m = text_mask((tw, th), text, ft, (0, -int(size * 0.16)), size * 0.04)
    page.paste(richter_strip(col, tw, th, stages=6), xy, m)
    return tw, th


def _para(d, xy, text, f, fill, maxw, lead):
    lines, cur = [], ""
    for wd in text.split(" "):
        cand = (cur + " " + wd).strip()
        if f.getlength(cand) > maxw and cur:
            lines.append(cur)
            cur = wd
        else:
            cur = cand
    lines.append(cur)
    x, y = xy
    for ln in lines:
        d.text((x, y), ln, font=f, fill=fill)
        y += lead
    return y


# ---------------------------------------------------------------- cover

def cover_sprezzatura(src: Image.Image, prints: dict, texts: dict, P: dict, W=2000, H=1234):
    page = Image.new("RGB", (W, H), P["paper"])
    crops = {k: src.crop(b) for k, b in prints.items()}
    # the dressed model: the large print, square to the page; the dress form: smaller, higher, a degree off
    m = crops["model"]
    s_m = 1000 / m.size[1]
    mi = matte(halation(m.resize((round(m.size[0] * s_m), 1000), Image.LANCZOS)), 24, 240)
    f = crops["form"]
    s_f = 720 / f.size[1]
    fi = matte(f.resize((round(f.size[0] * s_f), 720), Image.LANCZOS), 18, 244)
    # title first, so the prints are taped over its foot: the vest, divided, mirrored, repeated
    tw, th = _title(page, m, (0.50, 0.30, 0.56), texts["title"], 300, (70, 40), P)
    taped(page, fi, (170, 380), 1.2, P)
    mx = 1060
    taped(page, mi, (mx, 150), 0.0, P, tape=((0.22, -1), (0.78, 1)))
    d = ImageDraw.Draw(page)
    # copy: plain and light, set where a hand would write it
    fq = kr("light", 30)
    y = 520
    for line in texts["quote"]:
        d.text((600, y), line, font=fq, fill=P["ink"])
        y += 50
    tracked(d, (600, y + 40), texts["kicker"], kr("regular", 18), P["ink"], 6)
    it = fnt("serif_it", 16)
    tracked(d, (170, 380 + 720 + 46), f"Dress form, {f.size[0]} × {f.size[1]} px, ×{s_f:.2f}", it, P["note"], 0.3)
    tracked(d, (mx, 150 + 1000 + 40), f"Model, {m.size[0]} × {m.size[1]} px, ×{s_m:.2f} — a poor image, taped up "
            "as it is.", it, P["note"], 0.3)
    return grain(page, 0.022, 12, size=1.5), {
        "name": "MATCH — cover (sprezzatura)",
        "mood": "스프레차투라: nonchalance, concealed artistry, no affectation (Castiglione 1528)",
        "method": "Tillmans-style taped, unframed prints of varied size",
        "treatments": {"halation": "defaults, model print", "matte": "24/240 model, 18/244 dress form",
                       "Ruff shadow": "soft_jpeg factor 4 in the source's blue panel colour, ×1.16 at (−30, +24)",
                       "rotation": "dress form +1.2°", "Richter strip": "vest column, 6 stages, 55/45 toward paper"},
        "scale": {"model": s_m, "form": s_f}, "palette": P,
        "fonts": ["Noto Serif KR (OFL 1.1)", "Pretendard (OFL 1.1)", "Caladea Italic (Apache 2.0)"],
        "copy_notes": ["quote opens with \" and is never closed; kept as is"]}


# ---------------------------------------------------------------- spread

def spread_sprezzatura(src: Image.Image, photos, texts: dict, P: dict, W=2000, H=1231, inset=3):
    page = Image.new("RGB", (W, H), P["paper"])
    C = {p.key: src.crop((p.crop[0] + inset, p.crop[1] + inset, p.crop[2] - inset, p.crop[3] - inset))
         for p in photos}
    # (key, height on page, top-left, angle, matte): the night and the park share a top edge; the rest hang loose
    plan = (("night", 860, (110, 170), 0.0, (24, 240)), ("shop", 300, (620, 170), -1.0, (18, 244)),
            ("park", 380, (1090, 330), 0.0, (18, 244)), ("rock", 300, (1250, 790), 0.8, (18, 244)))
    tw = int(width(texts["title"], serif_kr("SemiBold", 190), 190 * 0.04)) + 30
    _title(page, C["rock"], (0.72, 0.18, 0.95), texts["title"], 190, (W - 70 - tw, 70), P)
    it = fnt("serif_it", 16)
    d = ImageDraw.Draw(page)
    scales = {}
    for key, hh, xy, ang, (b, w_) in plan:
        im = C[key]
        s = hh / im.size[1]
        pim = im.resize((round(im.size[0] * s), hh), Image.LANCZOS)
        pim = matte(halation(pim) if key == "night" else pim, b, w_)
        sz = taped(page, pim, xy, ang, P)
        scales[key] = s
        d = ImageDraw.Draw(page)
        tracked(d, (xy[0], xy[1] + sz[1] + 40), f"{im.size[0]} × {im.size[1]}, ×{s:.2f}", it, P["note"], 0.3)
    # copy on the left page, beside the night
    tx = 620
    d.text((tx, 640), texts["head"], font=kr("regular", 30), fill=P["ink"])
    _para(d, (tx, 700), texts["body"], kr("light", 20), P["ink"], 1000 - 60 - tx, 36)
    tracked(d, (tx, 1100), "Four prints, taped up unframed.", it, P["note"], 0.3)
    tracked(d, (tx, 1124), "Only cropped, scaled, turned a degree.", it, P["note"], 0.3)
    return grain(page, 0.02, 31, size=1.4), {
        "name": "MATCH. — spread (sprezzatura)",
        "mood": "스프레차투라: nonchalance, concealed artistry, no affectation (Castiglione 1528)",
        "method": "Tillmans-style taped, unframed prints; night and park share a top edge",
        "treatments": {"halation": "defaults, night", "matte": "24/240 night, 18/244 others",
                       "Ruff shadow": "soft_jpeg factor 4 in the source blue, ×1.16 at (−30, +24)",
                       "rotation": "shop −1.0°, rock +0.8°", "Richter strip": "rock-photo knit column, 6 stages"},
        "scales": scales, "palette": P,
        "fonts": ["Noto Serif KR (OFL 1.1)", "Pretendard (OFL 1.1)", "Caladea Italic (Apache 2.0)"]}
