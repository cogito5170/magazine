"""Read the atmosphere of pages, slides or photos as measurements, so the agent can choose a mood per page.

Everything here is a measurement or an explicitly labelled convention.  It does not name a mood.  The agent
maps these cues to a mood from docs/mood_library.md and states why.  Colour→emotion links are contested:
Valdez & Mehrabian (1994) relate brightness and saturation to pleasure/arousal, while Wilms & Oberfeld
(2018) report the opposite brightness→arousal sign.  So no emotion score is computed.
"""
from __future__ import annotations

import os

import numpy as np
from PIL import Image

from ..mathcore.color import dominant_colors, rgb_to_lab

# descriptor thresholds are conventions chosen for this tool, not standards
CUES = {"dark": 35.0, "bright": 65.0, "muted": 12.0, "vivid": 28.0, "flat": 14.0, "contrasty": 26.0}


def measure(img: Image.Image, max_side: int = 400) -> dict:
    im = img.convert("RGB")
    im.thumbnail((max_side, max_side))
    rgb = np.asarray(im, float) / 255
    lab = rgb_to_lab(rgb.reshape(-1, 3))
    L, a, b = lab[:, 0], lab[:, 1], lab[:, 2]
    C = np.hypot(a, b)
    hue = np.degrees(np.arctan2(b, a)) % 360
    w = C / (C.sum() + 1e-9)
    hx, hy = (w * np.cos(np.radians(hue))).sum(), (w * np.sin(np.radians(hue))).sum()
    warm = float(((b > 4) & (a > -6)).mean())
    cool = float(((b < -4) | (a < -8)).mean())
    m = {"lightness_mean": float(L.mean()), "lightness_sd": float(L.std()),
         "chroma_mean": float(C.mean()), "chroma_p90": float(np.percentile(C, 90)),
         "hue_mean_deg": float(np.degrees(np.arctan2(hy, hx)) % 360) if C.mean() > 3 else None,
         "warm_share": warm, "cool_share": cool,
         "dark_share": float((L < 25).mean()), "highlight_share": float((L > 85).mean()),
         "dominant": [{"hex": d["hex"], "share": round(d["share"], 3)} for d in dominant_colors(rgb, k=5)]}
    cues = []
    cues.append("dark/night" if m["lightness_mean"] < CUES["dark"] else
                "bright/day" if m["lightness_mean"] > CUES["bright"] else "mid-light")
    cues.append("muted" if m["chroma_mean"] < CUES["muted"] else "vivid" if m["chroma_mean"] > CUES["vivid"] else
                "moderate colour")
    cues.append("flat" if m["lightness_sd"] < CUES["flat"] else "contrasty" if m["lightness_sd"] > CUES["contrasty"]
                else "moderate contrast")
    cues.append("warm" if warm > cool + 0.15 else "cool" if cool > warm + 0.15 else "neutral temperature")
    if m["highlight_share"] > 0.02 and m["lightness_mean"] < CUES["dark"]:
        cues.append("point lights in the dark")
    m["cues"] = cues
    return m


def read_pdf(path: str, dpi: int = 72) -> list[dict]:
    import pypdfium2 as pdfium
    pdf = pdfium.PdfDocument(path)
    out = []
    for i in range(len(pdf)):
        page = pdf[i]
        img = page.render(scale=dpi / 72).to_pil()
        tp = page.get_textpage()
        text = tp.get_text_range().strip()
        w, h = page.get_size()
        out.append({"page": i + 1, "size_pt": [round(w, 1), round(h, 1)], "text": text[:600],
                    "text_chars": len(text), **measure(img)})
    pdf.close()
    return out


def read_any(path: str) -> list[dict]:
    if path.lower().endswith(".pdf"):
        return read_pdf(path)
    if os.path.isdir(path):
        files = sorted(f for f in os.listdir(path) if f.lower().endswith((".png", ".jpg", ".jpeg", ".webp", ".tif")))
        return [{"file": f, **measure(Image.open(os.path.join(path, f)))} for f in files]
    return [{"file": os.path.basename(path), **measure(Image.open(path))}]


def extract_pdf(path: str, out_dir: str, preview_dpi: int = 110) -> dict:
    """Page previews plus every embedded image at its native pixel size, with its effective ppi on the page.
    The originals inside a PDF are usually far better than a screenshot of it."""
    import pypdfium2 as pdfium
    import pypdfium2.raw as raw
    os.makedirs(out_dir, exist_ok=True)
    pdf = pdfium.PdfDocument(path)
    pages = []
    for i in range(len(pdf)):
        page = pdf[i]
        prev = os.path.join(out_dir, f"page_{i + 1:03d}.png")
        page.render(scale=preview_dpi / 72).to_pil().save(prev)
        imgs = []
        for j, obj in enumerate(page.get_objects(filter=[raw.FPDF_PAGEOBJ_IMAGE], max_depth=3)):
            try:
                pil = obj.get_bitmap(render=False).to_pil()
            except Exception as e:                        # unsupported filters are reported, not guessed
                imgs.append({"index": j, "error": f"{type(e).__name__}: {e}"})
                continue
            l, b, r, t = obj.get_bounds() if hasattr(obj, "get_bounds") else obj.get_pos()
            wpt, hpt = max(r - l, 1e-6), max(t - b, 1e-6)
            fp = os.path.join(out_dir, f"page_{i + 1:03d}_img_{j:02d}.png")
            pil.convert("RGB").save(fp)
            imgs.append({"index": j, "file": fp, "px": list(pil.size), "box_pt": [round(v, 1) for v in (l, b, r, t)],
                         "effective_ppi": round(min(pil.size[0] / (wpt / 72), pil.size[1] / (hpt / 72)), 1)})
        pages.append({"page": i + 1, "preview": prev, "size_pt": [round(v, 1) for v in page.get_size()],
                      "images": imgs})
    pdf.close()
    return {"source": os.path.abspath(path), "pages": pages}


def print_pdf(pages: list[str], out: str, trim_mm: tuple[float, float], bleed_mm: float = 3.0,
              min_ppi: float = 300.0) -> dict:
    """Assemble rendered page images into a PDF whose MediaBox includes bleed, with TrimBox/BleedBox set.
    Each image must already be drawn to trim + bleed.  Reports effective ppi; 300 ppi is a print convention,
    not a standard.  Output is RGB raster; press CMYK conversion is the printer's step and is not done here."""
    from reportlab.pdfgen import canvas
    mm = 72 / 25.4
    tw, th = trim_mm[0] * mm, trim_mm[1] * mm
    bl = bleed_mm * mm
    W, H = tw + 2 * bl, th + 2 * bl
    c = canvas.Canvas(out, pagesize=(W, H))
    report = []
    for p in pages:
        im = Image.open(p)
        ppi = min(im.size[0] / (W / 72), im.size[1] / (H / 72))
        aspect_err = abs(im.size[0] / im.size[1] - W / H) / (W / H)
        c.setTrimBox((bl, bl, bl + tw, bl + th))
        c.setBleedBox((0, 0, W, H))
        c.drawImage(p, 0, 0, W, H)
        c.showPage()
        report.append({"page": p, "px": list(im.size), "effective_ppi": round(ppi, 1),
                       "below_convention": ppi < min_ppi - 0.5, "aspect_mismatch": round(aspect_err, 4)})
    c.save()
    return {"out": os.path.abspath(out), "trim_mm": list(trim_mm), "bleed_mm": bleed_mm, "pages": report,
            "notes": ["RGB raster pages; text is rasterised at the page ppi",
                      "300 ppi is a common print convention, not a standard",
                      "colour conversion to the press profile is not done here"]}
