"""Shared pieces for the structure composers: photo prep, copy setting that proves it is verbatim, captions,
frames.  Photographs are only cropped, scaled, turned, mirrored or toned here; nothing is painted into them."""
from __future__ import annotations

import numpy as np
from PIL import Image, ImageDraw

from ..artdirect import cover as cover_fill, grain  # noqa: F401  (re-exported for the composers)
from ..contemporary import matte
from ..moodmachine import Layer, _face, _grade
from ..photo_led import tracked
from ..variants import fnt, width

W = 2000
KEYS = ("night", "park", "shop", "rock")


def prep(img, L: Layer, hero=False):
    return matte(_grade(img, L), *(L.hero_matte if hero else L.print_matte))


def scale_h(img, h):
    s = h / img.size[1]
    return img.resize((max(1, round(img.size[0] * s)), max(1, round(h))), Image.LANCZOS), s


def scale_w(img, w):
    s = w / img.size[0]
    return img.resize((max(1, round(w)), max(1, round(img.size[1] * s))), Image.LANCZOS), s


def fit(img, w, h):
    s = min(w / img.size[0], h / img.size[1])
    return img.resize((max(1, round(img.size[0] * s)), max(1, round(img.size[1] * s))), Image.LANCZOS), s


def wrap(text, f, maxw, tracking=0.0):
    lines, cur = [], ""
    for wd in text.split(" "):
        cand = (cur + " " + wd).strip()
        if width(cand, f, tracking) > maxw and cur:
            lines.append(cur)
            cur = wd
        else:
            cur = cand
    lines.append(cur)
    assert " ".join(lines) == text            # the copy is only broken at its own spaces
    return lines


def _union(a, b):
    return b if a is None else (min(a[0], b[0]), min(a[1], b[1]), max(a[2], b[2]), max(a[3], b[3]))


def text_at(d, xy, text, f, fill, tracking=0.0):
    """Set one line; returns its ink box."""
    tracked(d, xy, text, f, fill, tracking)
    bb = d.textbbox(xy, text, font=f)
    return (bb[0], bb[1], max(bb[2], int(xy[0] + width(text, f, tracking))), bb[3])


def set_copy(d, xy, texts, L: Layer, maxw, size=20, lead=None, head_size=28, color=None, tracking=0.0,
             face=None, weight=None, keys=("head", "kicker", "body")):
    """Head, kicker and body set horizontally from xy.  Returns (box, strings set)."""
    x, y = xy
    color = color or L.ink
    lead = lead or int(size * 1.7)
    box, done = None, []
    face = face or L.body_face
    if "head" in keys and texts.get("head"):
        fh = _face(face, "Medium" if face in ("serif", "sans") else "Regular", head_size)
        for ln in wrap(texts["head"], fh, maxw, tracking):
            box = _union(box, text_at(d, (x, y), ln, fh, color, tracking))
            y += int(head_size * 1.5)
        y += int(head_size * 0.5)
        done.append(texts["head"])
    if "kicker" in keys and texts.get("kicker"):
        fk = fnt("mono", 14) if L.caption_face == "mono" else fnt("serif_it", 17)
        box = _union(box, text_at(d, (x, y), texts["kicker"], fk, color, 3))
        y += 40
        done.append(texts["kicker"])
    if "body" in keys and texts.get("body"):
        fb = _face(face, weight or L.body_weight, size)
        for ln in wrap(texts["body"], fb, maxw, tracking):
            box = _union(box, text_at(d, (x, y), ln, fb, color, tracking))
            y += lead
        done.append(texts["body"])
    return box, done


def caption(d, xy, text, L: Layer, color=None):
    f = fnt("serif_it", 15) if L.caption_face == "serif_it" else fnt("mono", 12)
    tracked(d, xy, text, f, color or L.camel, 0.3)


def framed(img, mat, frame, mat_color, frame_color):
    w, h = img.size
    out = Image.new("RGB", (w + 2 * (mat + frame), h + 2 * (mat + frame)), frame_color)
    ImageDraw.Draw(out).rectangle((frame, frame, out.size[0] - frame - 1, out.size[1] - frame - 1), fill=mat_color)
    out.paste(img, (frame + mat, frame + mat))
    return out


def rotated(img, angle, fill):
    """Turn a print by `angle`° on a transparent ground; returns RGBA."""
    return img.convert("RGBA").rotate(angle, resample=Image.BICUBIC, expand=True, fillcolor=fill + (0,) if fill else None)


def paste_rgba(page, im, xy):
    page.paste(im, xy, im)
    return (xy[0], xy[1], xy[0] + im.size[0], xy[1] + im.size[1])


def finish(page, L: Layer, spec, seed=12):
    return grain(page, L.grain[0], seed, size=L.grain[1]), {"layer": dict(L.__dict__), **spec}


def mean_sat(img, box, gain=2.0):
    """Mean colour of a box with its saturation multiplied by `gain` (HSV), as an RGB tuple."""
    a = np.asarray(img.crop(box).convert("RGB"), float).reshape(-1, 3).mean(0) / 255
    import colorsys
    h, s, v = colorsys.rgb_to_hsv(*a)
    return tuple(int(round(c * 255)) for c in colorsys.hsv_to_rgb(h, min(1.0, s * gain), v))
