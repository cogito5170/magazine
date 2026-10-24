"""Sensory mood draft generator.

How a mood is represented
  A mood is a point on Russell's (1980) circumplex of affect:
  valence v = cos θ, arousal a = sin θ (θ: 0° pleasure, 90° arousal,
  315° relaxation).  Mood words are positions, not scores.

How sensory parameters are derived (each with its evidence type)
  colour brightness / saturation  – direction from Valdez & Mehrabian (1994):
      Pleasure = .69 B + .22 S,  Arousal = −.31 B + .60 S  (standardised B, S).
      The 2x2 system is inverted to obtain standardised (B, S) for (v, a).
      Converting standardised units into HSV values uses ANCHORS below,
      which are assumptions of this program (subjective_hypothesis).
      Wilms & Oberfeld (2018) report brighter colours with higher arousal,
      i.e. the brightness→arousal sign is contested.
  hue – V&M list blue, blue-green, green, purple(-blue), red-purple as most
      pleasant and yellow, green-yellow as least pleasant.
  text contrast – WCAG 2.2 SC 1.4.3 (≥ 4.5:1), a functional constraint.
  texture amplitude, whitespace, type choice, layout – no verified source
      in this project: recorded as subjective_hypothesis to be tested by
      the user's A/B choice.
The draft is then measured by the EDAS engine; the measurements are facts
about the draft, the mood is a hypothesis until people judge it.
"""
from __future__ import annotations

import colorsys
import json
import os
from typing import Optional

import numpy as np
from PIL import Image

from ..fontpaths import find
from ..mathcore.color import contrast_ratio, relative_luminance

VM = np.array([[0.69, 0.22], [-0.31, 0.60]])   # rows: pleasure, arousal ; cols: B, S (standardised)
ANCHORS = {"V_mean": 0.60, "V_sd": 0.17, "S_mean": 0.40, "S_sd": 0.25}   # assumption, not from a source
PLEASANT_HUES = {"blue-green": 175.0, "blue": 215.0, "purple-blue": 245.0}
UNPLEASANT_HUES = {"green-yellow": 75.0, "yellow": 55.0}

SOURCES = {
    "russell_1980": "Russell, J. A. (1980). A circumplex model of affect. J. Pers. Soc. Psychol. 39(6), 1161–1178. "
                    "doi:10.1037/h0077714",
    "valdez_mehrabian_1994": "Valdez, P. & Mehrabian, A. (1994). Effects of color on emotions. J. Exp. Psychol. Gen. "
                             "123(4), 394–409. PubMed 7996122 (abstract-level verification)",
    "wilms_oberfeld_2018": "Wilms, L. & Oberfeld, D. (2018). Color and emotion: effects of hue, saturation, and "
                           "brightness. Psychological Research (abstract-level verification)",
    "wcag22_sc143": "W3C WCAG 2.2, SC 1.4.3 Contrast (Minimum)",
}


def mood_point(angle_deg: float) -> dict:
    t = np.radians(angle_deg)
    return {"angle_deg": angle_deg, "valence": float(np.cos(t)), "arousal": float(np.sin(t))}


def colour_targets(v: float, a: float) -> dict:
    B, S = np.linalg.solve(VM, np.array([v, a]))
    V = float(np.clip(ANCHORS["V_mean"] + B * ANCHORS["V_sd"], 0.05, 0.97))
    Sat = float(np.clip(ANCHORS["S_mean"] + S * ANCHORS["S_sd"], 0.02, 0.95))
    hue_name, hue = (("blue-green", PLEASANT_HUES["blue-green"]) if v >= 0
                     else ("green-yellow", UNPLEASANT_HUES["green-yellow"]))
    return {"B_std": float(B), "S_std": float(S), "V": V, "S": Sat, "hue_name": hue_name, "hue_deg": hue}


def _hsv(h, s, v):
    return tuple(float(x) for x in colorsys.hsv_to_rgb(h / 360.0, s, v))


def palette(ct: dict) -> dict:
    h, s, v = ct["hue_deg"], ct["S"], ct["V"]
    paper = _hsv(h, s * 0.18, min(0.97, v + 0.16))
    field = _hsv(h, s, v)
    deep = _hsv(h, min(0.95, s * 1.15), v * 0.72)
    # text: same hue, darkened until WCAG 4.5:1 against paper (functional constraint)
    tv = v
    text = _hsv(h, min(0.9, s * 0.9), tv)
    while contrast_ratio(float(relative_luminance(np.array(text))), float(relative_luminance(np.array(paper)))) < 7.0 and tv > 0.05:
        tv -= 0.01
        text = _hsv(h, min(0.9, s * 0.9), tv)
    return {"paper": paper, "field": field, "deep": deep, "text": text,
            "text_contrast_on_paper": contrast_ratio(float(relative_luminance(np.array(text))),
                                                     float(relative_luminance(np.array(paper))))}


def sensory_field(w: int, h: int, pal: dict, arousal: float, seed: int = 0) -> np.ndarray:
    """Procedural 'photographic' field: low-frequency light gradient + grain.
    Grain amplitude and gradient steepness rise with arousal (hypothesis)."""
    rng = np.random.default_rng(seed)
    y, x = np.mgrid[0:h, 0:w] / np.array([h, w])[:, None, None]
    t = np.clip(0.15 + 0.85 * y + 0.08 * np.sin(2.2 * np.pi * x + 0.6), 0, 1) ** (1.6 - 0.5 * arousal)
    top, mid, bot = (np.array(pal["paper"]), np.array(pal["field"]), np.array(pal["deep"]))
    img = np.where(t[..., None] < 0.55, top + (mid - top) * (t[..., None] / 0.55),
                   mid + (bot - mid) * ((t[..., None] - 0.55) / 0.45))
    band = np.exp(-((y - 0.62) / 0.035) ** 2)[..., None]          # soft horizon line
    img = img * (1 - 0.10 * band) + 0.10 * band * top
    amp = 0.012 + 0.03 * max(0.0, arousal + 1) / 2
    img = img + rng.normal(0, amp, img.shape)
    return np.clip(img, 0, 1)


def generate(out_dir: str, name: str = "고요함 / Stillness", angle_deg: float = 315.0, seed: int = 7,
             title: str = "Still Water", subtitle: str = "고요한 물의 시간",
             body: Optional[list[str]] = None) -> dict:
    from reportlab.lib.utils import ImageReader
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.pdfgen import canvas
    os.makedirs(out_dir, exist_ok=True)
    mp = mood_point(angle_deg)
    ct = colour_targets(mp["valence"], mp["arousal"])
    pal = palette(ct)
    W, H = 600.0, 800.0
    pdfmetrics.registerFont(TTFont("MoodSerif", find("LiberationSerif-Regular.ttf")))
    pdfmetrics.registerFont(TTFont("MoodKo", find("wqy-zenhei.ttc"), subfontIndex=0))
    pdf_path = os.path.join(out_dir, "mood_draft.pdf")
    c = canvas.Canvas(pdf_path, pagesize=(W, H))
    c.setFillColorRGB(*pal["paper"])
    c.rect(0, 0, W, H, fill=1, stroke=0)
    m = 54.0
    fw, fh = W - 2 * m, 470.0
    field = sensory_field(1100, int(1100 * fh / fw), pal, mp["arousal"], seed)
    c.drawImage(ImageReader(Image.fromarray((field * 255).astype("uint8"))), m, H - m - fh, width=fw, height=fh)
    c.setFillColorRGB(*pal["text"])
    c.setFont("MoodSerif", 44)
    c.drawString(m, H - m - fh - 70, title)
    c.setFont("MoodKo", 14)
    c.drawString(m, H - m - fh - 98, subtitle)
    body = body or ["물결이 멈춘 자리에서 빛은 천천히 번진다.", "Light settles where the water stops moving."]
    c.setFont("MoodKo", 9.5)
    for i, line in enumerate(body):
        c.drawString(m, H - m - fh - 140 - i * 16, line)
    c.setFont("MoodSerif", 8)
    c.drawRightString(W - m, m - 18, f"mood draft · θ={angle_deg:.0f}° · seed {seed}")
    c.showPage()
    c.save()
    import pypdfium2 as pdfium
    png_path = os.path.join(out_dir, "mood_draft.png")
    pdfium.PdfDocument(pdf_path)[0].render(scale=2).to_pil().convert("RGB").save(png_path)
    decisions = [
        {"decision": "mood position", "value": mp, "claim_type": "empirical_study (framework)",
         "source": SOURCES["russell_1980"], "note": f"'{name}' placed at θ={angle_deg}° (relaxation quadrant)"},
        {"decision": "standardised brightness/saturation", "value": {"B_std": ct["B_std"], "S_std": ct["S_std"]},
         "claim_type": "empirical_study (direction)", "source": SOURCES["valdez_mehrabian_1994"],
         "note": "inverse of the published standardised regression; colour chips, not layouts"},
        {"decision": "HSV values from standardised units", "value": {"V": ct["V"], "S": ct["S"]},
         "claim_type": "subjective_hypothesis", "source": None,
         "note": f"anchors {ANCHORS} are assumptions of this program"},
        {"decision": "hue", "value": {"name": ct["hue_name"], "deg": ct["hue_deg"]},
         "claim_type": "empirical_study (direction)", "source": SOURCES["valdez_mehrabian_1994"],
         "note": "chosen from the most-pleasant hue group of the abstract"},
        {"decision": "brightness→arousal sign", "value": "negative in V&M",
         "claim_type": "contested", "source": SOURCES["wilms_oberfeld_2018"],
         "note": "W&O report brighter colours with higher arousal"},
        {"decision": "text colour", "value": {"rgb": pal["text"], "contrast": pal["text_contrast_on_paper"]},
         "claim_type": "official_standard (functional)", "source": SOURCES["wcag22_sc143"],
         "note": "darkened to ≥ 7:1 on paper (exceeds the 4.5:1 minimum)"},
        {"decision": "low grain, soft gradient, single focal field, wide margins, light serif + Korean sans",
         "value": None, "claim_type": "subjective_hypothesis", "source": None,
         "note": "no verified evidence for layout/type → mood; must be tested by A/B choice"},
    ]
    spec = {"mood": name, "target": mp, "colour": ct, "palette": {k: (list(v) if isinstance(v, tuple) else v)
                                                                   for k, v in pal.items()},
            "decisions": decisions, "files": {"pdf": pdf_path, "png": png_path}, "seed": seed,
            "status": "hypothesis: mood not validated by human judgments"}
    with open(os.path.join(out_dir, "mood_spec.json"), "w", encoding="utf-8") as fh:
        json.dump(spec, fh, ensure_ascii=False, indent=2)
    return spec
