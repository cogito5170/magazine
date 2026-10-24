"""Page overlays: object bounding boxes, estimated grid, saliency heatmap,
visual centre of mass.  Colours follow a validated categorical order
(text = slot 1 blue, image = slot 2 orange, vector = slot 3 aqua)."""
from __future__ import annotations

import numpy as np
from PIL import Image, ImageDraw

from ..mathcore.imaging import resize

KIND_COLOR = {"text": (42, 120, 214), "image": (235, 104, 52), "vector": (27, 175, 122)}
GRID_COLOR = (98, 80, 214)


def page_image(pm) -> Image.Image:
    return Image.fromarray((np.clip(pm.render, 0, 1) * 255).astype("uint8"))


def overlay_objects_grid(pm, grid: dict | None = None, com=None) -> Image.Image:
    im = page_image(pm).convert("RGBA")
    lay = Image.new("RGBA", im.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    s = pm.render_scale
    if grid and grid.get("columns"):
        c = grid["columns"]
        for x0, x1 in zip(c["starts"], c["ends"]):
            d.rectangle([x0 * s, 0, x1 * s, im.size[1]], fill=GRID_COLOR + (28,))
            d.line([x0 * s, 0, x0 * s, im.size[1]], fill=GRID_COLOR + (160,), width=1)
            d.line([x1 * s, 0, x1 * s, im.size[1]], fill=GRID_COLOR + (160,), width=1)
    if grid and grid.get("rows"):
        r = grid["rows"]
        for y in r["starts"] + r["ends"]:
            d.line([0, y * s, im.size[0], y * s], fill=GRID_COLOR + (90,), width=1)
    for o in pm.objects:
        b = [v * s for v in o.box]
        col = KIND_COLOR.get(o.kind, (80, 80, 80))
        d.rectangle(b, outline=col + (255,), width=2)
        d.text((b[0] + 3, b[1] + 2), o.id.split("-")[-1], fill=col + (255,))
    if com:
        cx, cy = com[0] * im.size[0], com[1] * im.size[1]
        d.ellipse([cx - 7, cy - 7, cx + 7, cy + 7], outline=(11, 11, 11, 255), width=3)
        d.line([cx - 12, cy, cx + 12, cy], fill=(11, 11, 11, 255), width=2)
        d.line([cx, cy - 12, cx, cy + 12], fill=(11, 11, 11, 255), width=2)
    return Image.alpha_composite(im, lay).convert("RGB")


def saliency_heatmap(pm, saliency: np.ndarray, alpha: float = 0.55) -> Image.Image:
    """Sequential single-hue ramp (light -> dark blue) over the page."""
    H, W = pm.render.shape[:2]
    s = resize(saliency, W, H)
    s = s / (s.max() + 1e-12)
    lo = np.array([0.89, 0.93, 0.98])
    hi = np.array([0.04, 0.24, 0.55])
    col = lo[None, None, :] * (1 - s[..., None]) + hi[None, None, :] * s[..., None]
    a = (alpha * s)[..., None]
    out = pm.render * (1 - a) + col * a
    return Image.fromarray((np.clip(out, 0, 1) * 255).astype("uint8"))
