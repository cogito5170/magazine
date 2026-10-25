"""Shared pieces for the 'declaration' family the user liked (022 red bars, "이건 좋아", 2026-10-25):
a black-and-white photograph, one loud colour, the copy set like a statement.  Written by the mood writer for
diagonal, monochrome, poster and intertitle.  Photographs are only cropped, scaled, turned and toned."""
from __future__ import annotations

from PIL import Image, ImageDraw

from ..moodmachine import _face, _grade
from ..variants import width
from ._common import cover_fill, scale_h, wrap


def bw_hero(crops, persons, L, size, prefer="park"):
    """The widest photo (park on the spread, the model on the cover), toned by the layer, cover-filled."""
    key = prefer if prefer in crops and crops[prefer].size[0] >= 600 else \
        max(crops, key=lambda k: crops[k].size[0] * crops[k].size[1])
    img, pb = crops[key], persons[key]
    bw = _grade(img, L)
    hero, info = cover_fill(bw, size, focus=(((pb[0] + pb[2]) / 2) / img.size[0], 0.5))
    return key, img, bw, hero, info


def copy_lines(texts, L, size, maxw, keys=("kicker", "head", "body")):
    """(key, line, font) for every copy line, broken only at the copy's own spaces."""
    out = []
    for k in keys:
        if not texts.get(k):
            continue
        f = _face("sans", "Bold" if k != "body" else L.body_weight, size + (6 if k != "body" else 0))
        for ln in (wrap(texts[k], f, maxw) if width(texts[k], f) > maxw else [texts[k]]):
            out.append((k, ln, f))
    return out


def panel_line(page, xy, text, f, fg, bg, pad=(18, 10)):
    """One copy line on its own solid panel (the judge measures text over a photo only on a panel)."""
    asc, desc = f.getmetrics()
    tw, th = int(width(text, f)) + 2 * pad[0], asc + desc + 2 * pad[1]
    d = ImageDraw.Draw(page)
    d.rectangle((xy[0], xy[1], xy[0] + tw, xy[1] + th), fill=bg)
    d.text((xy[0] + pad[0], xy[1] + pad[1]), text, font=f, fill=fg)
    return (xy[0], xy[1], xy[0] + tw, xy[1] + th)


def mask_paste(page, mask, xy, colour):
    page.paste(Image.new("RGB", mask.size, colour), xy, mask)
    return (xy[0], xy[1], xy[0] + mask.size[0], xy[1] + mask.size[1])


def bordered(R, img, L, h, colour, border=8):
    im, s = scale_h(R.print_(_grade(img, L)), h)
    out = Image.new("RGB", (im.size[0] + 2 * border, im.size[1] + 2 * border), colour)
    out.paste(im, (border, border))
    return out, s


def strip_paste(R, page, mask, xy, src, colour, mix=0.2):
    """The title in its colour, carrying the series DNA: Richter stripes from the photograph, pulled ~80% toward
    the colour so the word keeps its one loud colour (as the liked bars title)."""
    fill = R.strip_fill(src, (0.5, 0.05, 0.95), mask.size[0], mask.size[1], colour, mix=mix, toward=colour)
    page.paste(fill, xy, mask)
    return (xy[0], xy[1], xy[0] + mask.size[0], xy[1] + mask.size[1])
