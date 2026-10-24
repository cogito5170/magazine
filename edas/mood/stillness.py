"""'고요함 / Stillness' — four expression methods.

Each method is a different route to the same mood position (Russell
circumplex, low arousal / mildly positive valence) and records, per design
decision, the evidence type:

  M1 atmosphere  – layered fractal ridgelines, aerial perspective, mist and a
                   near-perfect water mirror.   Fractal profiles with
                   D ≈ 1.3 (Taylor's stress-recovery findings, secondary
                   sources only); low saturation / high brightness
                   (Valdez & Mehrabian 1994, direction).
  M2 emptiness   – typographic page with very low visual complexity
                   (Berlyne: complexity raises arousal potential; mechanism
                   contested).
  M3 curvature   – only curved, low-contrast forms (Bar & Neta 2006:
                   preference for curves, sharp contours as threat cues).
  M4 breath      – motion paced at 6 cycles / min (slow-breathing evidence:
                   Zaccaro et al. 2018 review; 2023 meta-analysis: modest
                   effect on negative emotion).  Applies only if the viewer
                   breathes with it.

Everything not covered by those sources (composition, type, texture,
copy) is a design hypothesis.  Whether a draft *feels* still is decided by
people, through the A/B 'stillness' criterion.
"""
from __future__ import annotations

import colorsys
import json
import os
from typing import Optional

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from ..fontpaths import find
from ..mathcore.color import contrast_ratio, relative_luminance
from ..mathcore.fractal import box_counting_dimension, midpoint_profile
from ..mathcore.imaging import gaussian_blur, local_maxima, resize, resize_max
from ..mathcore.saliency import spectral_residual
from ..mathcore.stats import shannon_entropy

W, H = 1800, 2400
FONTS = {
    "thin": find("InterDisplay-Thin.otf"),
    "xlight": find("InterDisplay-ExtraLight.otf"),
    "light": find("InterDisplay-Light.otf"),
    "serif_it": find("Caladea-Italic.ttf"),
    "ko": find("wqy-zenhei.ttc"),
}
SRC = {
    "russell": "Russell 1980, J. Pers. Soc. Psychol. 39(6):1161–1178 (verified bibliographic record)",
    "vm": "Valdez & Mehrabian 1994, J. Exp. Psychol. Gen. 123(4):394–409 (abstract-level)",
    "taylor": "R. Taylor et al., fractal D 1.3–1.5 and stress recovery (secondary accounts only; original papers not read)",
    "berlyne": "Berlyne 1971, Aesthetics and Psychobiology (framework; arousal mechanism contested)",
    "barneta": "Bar & Neta 2006, Psychol. Sci. 17(8):645–648 (abstract-level)",
    "breath": "Zaccaro et al. 2018, Front. Hum. Neurosci. (review, <10 breaths/min); 2023 meta-analysis, Mindfulness",
    "wcag": "W3C WCAG 2.2 SC 1.4.3 (functional legibility constraint)",
}


def hsv(h, s, v):
    return np.array(colorsys.hsv_to_rgb(h / 360.0, s, v))


def font(key, size):
    return ImageFont.truetype(FONTS[key], size=size, index=0)


def tracked(draw, xy, text, f, fill, tracking=0.0):
    x, y = xy
    for ch in text:
        draw.text((x, y), ch, font=f, fill=fill)
        x += f.getlength(ch) + tracking
    return x


def grain(img, amp, seed):
    rng = np.random.default_rng(seed)
    n = rng.normal(0, amp, img.shape[:2])[..., None]
    return np.clip(img + n, 0, 1)


def to_pil(a):
    return Image.fromarray((np.clip(a, 0, 1) * 255).astype("uint8"))


def lerp(a, b, t):
    return a + (b - a) * t


# ---------------------------------------------------------------- M1
def m1_atmosphere(seed: int = 11, hurst: float = 0.7, smooth: int = 25, n_pow: int = 9,
                  amp_scale: float = 1.0) -> tuple[Image.Image, dict]:
    yh = int(0.585 * H)
    yy = np.arange(H)[:, None] / H
    c_top, c_hz = hsv(214, 0.075, 0.885), hsv(32, 0.07, 0.965)
    t = np.clip(yy / (yh / H), 0, 1) ** 1.7
    sky = lerp(c_top, c_hz, t[..., None]) * np.ones((H, W, 3))
    img = sky.copy()
    c_near = hsv(216, 0.13, 0.50)
    layers = [(0.030, 0.150, 0.16), (0.016, 0.105, 0.30), (0.008, 0.066, 0.46), (0.000, 0.034, 0.64)]
    ridges, contour = [], np.zeros((H, W), bool)
    X = np.linspace(0, 1, W)
    for k, (base, amp, w) in enumerate(layers):
        p = midpoint_profile(n_pow, hurst, seed + 17 * k)
        p = np.interp(X, np.linspace(0, 1, p.size), p)
        if smooth > 1:
            win = np.hanning(smooth) / np.hanning(smooth).sum()
            p = np.convolve(np.pad(p, smooth // 2, mode="edge"), win, "valid")[:W]
        p = (p - p.min()) / (np.ptp(p) + 1e-12)
        ry = yh - (base + amp * amp_scale * p) * H
        ridges.append(ry)
        col = lerp(c_hz, c_near, w)
        rows = np.arange(yh)[:, None]
        inside = rows >= ry[None, :]
        peak = ry.min()
        depth = np.clip((rows - peak) / max(yh - peak, 1), 0, 1) * np.ones((1, W))
        mist = 0.66 * depth ** 1.6                      # horizontal mist rising from the water
        layer = lerp(col[None, None, :], c_hz[None, None, :], mist[..., None])
        img[:yh] = np.where(inside[..., None], layer, img[:yh])
        ys = np.clip(np.round(ry).astype(int), 0, H - 1)
        for i in range(W - 1):                                     # connected contour
            a, b = sorted((ys[i], ys[i + 1]))
            contour[a:b + 1, i] = True
    # water: near-perfect mirror (stillness), slightly darker, lower contrast
    src = np.clip(2 * yh - np.arange(yh, H), 0, yh - 1)
    refl = img[src].copy()
    rows = np.arange(H - yh)[:, None]
    dx = (0.9 * np.sin(2 * np.pi * rows / 41.0) * (rows / (H - yh))).astype(int)
    cols = np.clip(np.arange(W)[None, :] + dx, 0, W - 1)
    refl = refl[np.arange(H - yh)[:, None], cols]
    refl = lerp(refl, c_hz, 0.16) * 0.955
    img[yh:] = refl
    img[yh - 1:yh + 1] = lerp(img[yh - 1:yh + 1], c_hz, 0.6)       # faint shoreline light
    img = grain(img, 0.0085, seed)
    im = to_pil(img)
    d = ImageDraw.Draw(im)
    ink = tuple(int(255 * v) for v in hsv(218, 0.18, 0.28))
    x0 = int(0.083 * W)
    tracked(d, (x0, int(0.845 * H)), "BEFORE DAWN", font("light", 40), ink, tracking=15)
    tracked(d, (x0, int(0.845 * H) + 70), "새벽이 오기 전, 물은 하늘을 그대로 담는다", font("ko", 29), ink, tracking=3)
    xe = tracked(d, (W - x0 - 190, int(0.957 * H)), "01  —  ", font("thin", 24), ink, tracking=4)
    tracked(d, (xe, int(0.957 * H) - 2), "고요", font("ko", 22), ink, tracking=4)
    D = box_counting_dimension(contour[: yh + 2])
    return im, {"method": "M1 atmosphere", "hurst": hurst, "smoothing_window": smooth, "profile_points": 2 ** n_pow + 1, "profile_dimension_target": 2 - hurst,
                "contour_box_counting_D": D["D"], "horizon_y_fraction": yh / H, "ink_rgb": ink,
                "decisions": [
                    {"decision": "mood position θ=315° (relaxation)", "claim_type": "empirical_study (framework)", "source": SRC["russell"]},
                    {"decision": "light, desaturated palette (V≈0.89–0.97, S≈0.07)", "claim_type": "empirical_study (direction)", "source": SRC["vm"]},
                    {"decision": f"fractal ridgelines, H={hurst} (profile D≈{2 - hurst:.1f})", "claim_type": "empirical_study (weak: secondary sources)", "source": SRC["taylor"]},
                    {"decision": "mirror reflection, mist, aerial perspective, low horizon", "claim_type": "subjective_hypothesis", "source": None},
                    {"decision": "spaced light sans caps + small Korean line", "claim_type": "subjective_hypothesis", "source": None},
                ]}


# ---------------------------------------------------------------- M2
def m2_emptiness(seed: int = 5) -> tuple[Image.Image, dict]:
    paper = hsv(40, 0.035, 0.955)
    rng = np.random.default_rng(seed)
    fib = gaussian_blur(rng.normal(0, 1, (H // 4, W // 4)), 1.2)
    fib = resize(fib / (np.abs(fib).max() + 1e-9), W, H)
    img = np.ones((H, W, 3)) * paper + 0.006 * fib[..., None]
    # a single faint moon: soft disc, low contrast
    cy, cx, r = 0.305 * H, 0.70 * W, 44
    yy, xx = np.mgrid[0:H, 0:W]
    dist = np.hypot(yy - cy, xx - cx)
    disc = np.clip((r - dist) / 2.5 + 0.5, 0, 1)
    halo = np.exp(-((dist - r).clip(0) / 120) ** 2) * 0.25 * (dist > r)
    moon = hsv(212, 0.06, 0.86)
    img = lerp(img, moon[None, None, :], (0.85 * disc + halo)[..., None])
    img = grain(img, 0.006, seed)
    im = to_pil(img)
    d = ImageDraw.Draw(im)
    ink = tuple(int(255 * v) for v in hsv(30, 0.08, 0.24))
    soft = tuple(int(255 * v) for v in hsv(30, 0.06, 0.42))
    x0 = int(0.125 * W)
    y0 = int(0.655 * H)
    d.line([(x0, y0 - 48), (x0 + 120, y0 - 48)], fill=soft, width=1)
    tracked(d, (x0, y0), "고요", font("ko", 62), ink, tracking=18)
    d.text((x0, y0 + 112), "Stillness is not the absence of sound,", font=font("serif_it", 34), fill=ink)
    d.text((x0, y0 + 158), "but the room it leaves.", font=font("serif_it", 34), fill=ink)
    tracked(d, (x0, y0 + 236), "소리가 없는 것이 아니라, 소리가 머물 자리를 남겨두는 것", font("ko", 23), soft, tracking=2)
    tracked(d, (W - x0 - 60, int(0.957 * H)), "02", font("light", 24), soft, tracking=4)
    return im, {"method": "M2 emptiness", "ink_rgb": ink, "decisions": [
        {"decision": "mood position θ=315°", "claim_type": "empirical_study (framework)", "source": SRC["russell"]},
        {"decision": "minimal visual complexity: one soft form, one text block", "claim_type": "empirical_study (framework, contested)", "source": SRC["berlyne"]},
        {"decision": "warm paper, low-contrast moon", "claim_type": "empirical_study (direction) + hypothesis", "source": SRC["vm"]},
        {"decision": "asymmetric placement, italic serif line, Korean echo line", "claim_type": "subjective_hypothesis", "source": None},
    ]}


# ---------------------------------------------------------------- M3
def m3_curvature(seed: int = 3) -> tuple[Image.Image, dict]:
    yy = np.arange(H)[:, None] / H
    base = lerp(hsv(206, 0.055, 0.93), hsv(208, 0.10, 0.80), (yy ** 1.3)[..., None]) * np.ones((H, W, 3))
    cy, cx = 0.43 * H, 0.52 * W
    Y, X = np.mgrid[0:H, 0:W].astype(float)
    rx = np.hypot((X - cx), (Y - cy) / 0.34)                       # surface seen at a low angle
    lam = 120 + 0.10 * rx                                           # rings widen outward
    env = np.exp(-((rx - 260) / 330) ** 2) * np.clip(rx / 90.0, 0, 1)   # a dissolving packet, not a target
    wave = np.cos(2 * np.pi * rx / lam) * env
    wave = gaussian_blur(wave, 5.0)
    shade = 0.022 * wave
    img = np.clip(base + shade[..., None], 0, 1)
    glint = np.exp(-(rx / 26.0) ** 2) * 0.18
    img = lerp(img, hsv(40, 0.04, 0.99)[None, None, :], glint[..., None])
    img = grain(img, 0.007, seed)
    im = to_pil(img)
    d = ImageDraw.Draw(im)
    ink = tuple(int(255 * v) for v in hsv(212, 0.20, 0.30))
    x0 = int(0.083 * W)
    tracked(d, (x0, int(0.86 * H)), "after the ripple", font("xlight", 40), ink, tracking=6)
    tracked(d, (x0, int(0.86 * H) + 66), "파문이 가라앉는 시간", font("ko", 29), ink, tracking=4)
    tracked(d, (W - x0 - 60, int(0.957 * H)), "03", font("light", 24), ink, tracking=4)
    return im, {"method": "M3 curvature", "ink_rgb": ink, "decisions": [
        {"decision": "mood position θ=315°", "claim_type": "empirical_study (framework)", "source": SRC["russell"]},
        {"decision": "only curved contours, no sharp transitions in the image", "claim_type": "empirical_study (preference/threat cue)", "source": SRC["barneta"]},
        {"decision": "ring contrast ≤ 3.5% of brightness, decaying outward", "claim_type": "subjective_hypothesis", "source": None},
        {"decision": "light blue-grey field", "claim_type": "empirical_study (direction)", "source": SRC["vm"]},
    ], "note": "curvature preference ≠ calm; the link to stillness is a hypothesis"}


# ---------------------------------------------------------------- M4
BREATH_HTML = """<!doctype html><html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Breath — Stillness</title>
<style>
:root{--top:#dfe3e8;--hz:#f6f1ea;--orb:#eef0f2;--ink:#3b4350}
html,body{margin:0;height:100%;background:var(--hz)}
body{display:grid;place-items:center;background:linear-gradient(180deg,var(--top),var(--hz) 70%);
font-family:"Inter Display","Inter",system-ui,sans-serif;color:var(--ink);overflow:hidden}
.orb{width:42vmin;height:42vmin;border-radius:50%;
background:radial-gradient(circle at 50% 45%,#fbfaf7 0%,var(--orb) 55%,rgba(238,240,242,0) 72%);
animation:breathe 10s ease-in-out infinite}
@keyframes breathe{0%{transform:scale(.82);opacity:.75}40%{transform:scale(1.06);opacity:1}100%{transform:scale(.82);opacity:.75}}
.cue{position:fixed;bottom:9vh;left:0;right:0;text-align:center;letter-spacing:.35em;font-weight:200;font-size:14px}
.cue span{animation:inout 10s ease-in-out infinite;opacity:0;position:absolute;left:0;right:0}
.cue .out{animation-name:outin}
@keyframes inout{0%,5%{opacity:0}12%,33%{opacity:.9}40%,100%{opacity:0}}
@keyframes outin{0%,42%{opacity:0}52%,88%{opacity:.9}96%,100%{opacity:0}}
.note{position:fixed;top:4vh;left:6vw;font-size:12px;letter-spacing:.2em;font-weight:200;opacity:.7}
@media (prefers-reduced-motion:reduce){.orb,.cue span{animation:none}.cue .in{opacity:.9}}
</style></head><body>
<div class="note">04 — 고요 · BREATH</div>
<div class="orb" role="img" aria-label="slowly expanding and contracting light, 6 cycles per minute"></div>
<div class="cue"><span class="in">들이쉬고 &nbsp;·&nbsp; inhale</span><span class="out">내쉬고 &nbsp;·&nbsp; exhale</span></div>
</body></html>"""


def m4_breath_frame() -> Image.Image:
    """Static frame of M4 for the contact sheet (orb at mid-inhale)."""
    yy = np.arange(H)[:, None] / H
    img = lerp(np.array([0xdf, 0xe3, 0xe8]) / 255, np.array([0xf6, 0xf1, 0xea]) / 255,
               np.clip(yy / 0.7, 0, 1)[..., None]) * np.ones((H, W, 3))
    Y, X = np.mgrid[0:H, 0:W]
    r = np.hypot(Y - H / 2, X - W / 2) / (0.21 * min(W, H) * 1.06 / 0.72)
    orb = np.clip(1 - r, 0, 1) ** 1.4
    img = lerp(img, np.array([0.985, 0.98, 0.97]), orb[..., None] * 0.9)
    im = to_pil(img)
    d = ImageDraw.Draw(im)
    ink = (59, 67, 80)
    tracked(d, (int(0.06 * W), int(0.04 * H)), "04 — 고요 · BREATH", font("ko", 24), ink, tracking=4)
    tracked(d, (int(0.36 * W), int(0.88 * H)), "들이쉬고 · inhale", font("ko", 30), ink, tracking=8)
    return im


# ---------------------------------------------------------------- measurement
def measure(im: Image.Image, cfg: dict) -> dict:
    from ..modules.photography import image_features
    rgb = np.asarray(im.convert("RGB"), float) / 255.0
    f = image_features(rgb, cfg)
    g, _ = resize_max(rgb.mean(2), 400)
    sal = spectral_residual(g)
    sm = gaussian_blur(sal, 2.0)
    pk = local_maxima(sm, max(1, int(0.05 * max(sm.shape))), 0.5 * sm.max())
    return {"mean_luminance_C03": f["C03"], "luminance_contrast_C05": f["C05"], "mean_saturation_C06": f["C06"],
            "color_entropy_bits_C08": f["C08"], "edge_density_C10": f["C10"],
            "saliency_entropy_bits_D15": shannon_entropy(sal), "focal_points_D16": len(pk),
            "symmetry_lr_C16": f["C16"]["left_right"]}


def text_contrast(im: Image.Image, ink, box) -> float:
    a = np.asarray(im.convert("RGB").crop(box), float).reshape(-1, 3) / 255.0
    far = np.linalg.norm(a - np.asarray(ink) / 255.0, axis=1) > 0.2
    bg = np.median(a[far], axis=0)
    return contrast_ratio(float(relative_luminance(np.asarray(ink) / 255.0)), float(relative_luminance(bg)))


def save_pdf(im: Image.Image, path: str):
    im.convert("RGB").save(path, "PDF", resolution=300.0)


def generate_all(out_dir: str, cfg: Optional[dict] = None) -> dict:
    from ..config import load_config
    cfg = cfg or load_config()
    os.makedirs(out_dir, exist_ok=True)
    drafts = {}
    variants = (("M1_atmosphere", m1_atmosphere, {}),
                ("M1b_atmosphere_rough", m1_atmosphere, {"hurst": 0.4, "smooth": 5, "n_pow": 11}),
                ("M2_emptiness", m2_emptiness, {}), ("M3_curvature", m3_curvature, {}))
    for key, fn, kw in variants:
        im, spec = fn(**kw)
        if key.startswith("M1"):
            D = spec["contour_box_counting_D"]
            inside = D is not None and 1.3 <= D <= 1.5
            spec["decisions"][2]["measured_D"] = D
            spec["decisions"][2]["claim_type"] = ("empirical_study (weak: secondary sources); measured D inside 1.3–1.5"
                                                  if inside else "subjective_hypothesis: measured D outside the 1.3–1.5 range "
                                                  "of the cited finding, so it does not support this draft")
        png = os.path.join(out_dir, f"{key}.png")
        im.save(png, optimize=True)
        save_pdf(im, os.path.join(out_dir, f"{key}.pdf"))
        spec["measured"] = measure(im, cfg)
        spec["text_contrast_bottom_band"] = text_contrast(im, spec["ink_rgb"], (0, int(0.8 * H), W, H))
        spec["status"] = "hypothesis: stillness not yet judged by people"
        drafts[key] = {"png": png, "spec": spec}
    with open(os.path.join(out_dir, "M4_breath.html"), "w", encoding="utf-8") as fh:
        fh.write(BREATH_HTML)
    frame = m4_breath_frame()
    frame.save(os.path.join(out_dir, "M4_breath_frame.png"), optimize=True)
    drafts["M4_breath"] = {"html": os.path.join(out_dir, "M4_breath.html"), "spec": {
        "method": "M4 breath", "cycle_s": 10, "rate_per_min": 6, "inhale_s": 4, "exhale_s": 6,
        "decisions": [
            {"decision": "6 cycles/min pacing (0.1 Hz), longer exhale", "claim_type": "empirical_study",
             "source": SRC["breath"], "note": "effect requires the viewer to breathe along; modest effect sizes"},
            {"decision": "orb, gradient, cue typography", "claim_type": "subjective_hypothesis", "source": None},
            {"decision": "prefers-reduced-motion respected (static)", "claim_type": "official_standard (accessibility practice)", "source": None}],
        "measured": measure(frame, cfg)}}
    # contact sheet
    order = ("M1_atmosphere", "M1b_atmosphere_rough", "M2_emptiness", "M3_curvature")
    thumbs = [Image.open(drafts[k]["png"]) for k in order] + [frame]
    tw = 520
    th = int(tw * H / W)
    sheet = Image.new("RGB", (len(thumbs) * tw + (len(thumbs) + 1) * 36, th + 72), (244, 242, 238))
    for i, t in enumerate(thumbs):
        sheet.paste(t.resize((tw, th), Image.LANCZOS), (36 + i * (tw + 36), 36))
    sheet.save(os.path.join(out_dir, "stillness_contact_sheet.png"), optimize=True)
    build_ab(out_dir, drafts)
    with open(os.path.join(out_dir, "stillness_spec.json"), "w", encoding="utf-8") as fh:
        json.dump({k: v["spec"] for k, v in drafts.items()}, fh, ensure_ascii=False, indent=2, default=float)
    return drafts


def build_ab(out_dir: str, drafts: dict, baseline_png: Optional[str] = None) -> str:
    """Manifest + A/B page: M1 vs M1b isolates the fractal-roughness claim;
    the remaining pairs compare methods (and the rejected v1 draft if given)."""
    import hashlib
    from ..preference.interface import build_ab_page
    stim = []
    for k in ("M1_atmosphere", "M1b_atmosphere_rough", "M2_emptiness", "M3_curvature"):
        with open(drafts[k]["png"], "rb") as fh:
            stim.append({"stimulus_id": k, "file": os.path.basename(drafts[k]["png"]),
                         "sha256": hashlib.sha256(fh.read()).hexdigest(), "font": k, "variant": "draft"})
    base = baseline_png or os.path.join(os.path.dirname(out_dir.rstrip("/")), "mood", "mood_draft.png")
    if os.path.exists(base):
        dst = os.path.join(out_dir, "v1_still_water.png")
        Image.open(base).convert("RGB").resize((W, H), Image.LANCZOS).save(dst)
        stim.append({"stimulus_id": "v1_still_water", "file": "v1_still_water.png", "sha256": None,
                     "font": "v1_still_water", "variant": "rejected baseline"})
    ids = [s["stimulus_id"] for s in stim]
    pairs = [{"a": "M1_atmosphere", "b": "M1b_atmosphere_rough", "purpose": "fractal roughness D 1.17 vs 1.33"}]
    for i in range(len(ids)):
        for j in range(i + 1, len(ids)):
            if {ids[i], ids[j]} != {"M1_atmosphere", "M1b_atmosphere_rough"}:
                pairs.append({"a": ids[i], "b": ids[j], "purpose": "method comparison"})
    man = {"experiment": "mood", "word": "고요함 / Stillness", "stimuli": stim, "pairs": pairs,
           "conditions": {"size_px": [W, H], "display": "same canvas size, PNG"}}
    mp = os.path.join(out_dir, "manifest.json")
    with open(mp, "w", encoding="utf-8") as fh:
        json.dump(man, fh, ensure_ascii=False, indent=2)
    return build_ab_page(mp, os.path.join(out_dir, "stillness_AB.html"), page_id="mood:stillness",
                         project_id="mood")
