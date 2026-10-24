"""Coordinate helpers for reading photo regions and person boxes off a source spread."""
from __future__ import annotations

from PIL import Image, ImageDraw, ImageFont


def grid_zoom(img: Image.Image, region=None, zoom: int = 3, step: int = 10) -> Image.Image:
    """Enlarge `region` (source px) with nearest neighbour and draw ticks every `step` px, labelled in
    absolute source coordinates every 5 ticks, so boxes can be read off directly."""
    x0, y0, x1, y1 = region or (0, 0, img.size[0], img.size[1])
    c = img.convert("RGB").crop((x0, y0, x1, y1)).resize(((x1 - x0) * zoom, (y1 - y0) * zoom), Image.NEAREST)
    pad = 36
    out = Image.new("RGB", (c.size[0] + pad, c.size[1] + pad), (255, 255, 255))
    out.paste(c, (pad, pad))
    d = ImageDraw.Draw(out)
    f = ImageFont.load_default()
    red = (220, 0, 0)
    for v in range(x0 - x0 % step, x1 + 1, step):
        if v < x0:
            continue
        X = pad + (v - x0) * zoom
        major = v % (step * 5) == 0
        d.line([(X, pad - (12 if major else 5)), (X, pad + (out.size[1] if major else 0))],
               fill=red if major else (240, 120, 120), width=1)
        if major:
            d.text((X + 2, 2), str(v), fill=red, font=f)
    for v in range(y0 - y0 % step, y1 + 1, step):
        if v < y0:
            continue
        Y = pad + (v - y0) * zoom
        major = v % (step * 5) == 0
        d.line([(pad - (12 if major else 5), Y), (pad + (out.size[0] if major else 0), Y)],
               fill=red if major else (240, 120, 120), width=1)
        if major:
            d.text((2, Y + 2), str(v), fill=red, font=f)
    return out
