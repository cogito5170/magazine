"""The approved recipe, as calls every structure composer must make (SKILL.md §4).  The values are the ones the
approved spreads use; nothing here changes an approved function, it only calls them.

    boldness      one strong structural idea, a title at display size (title box >= 5% of the page; the
                  approved pages measure 6-14%), and it still reads
    series DNA    Richter strip title (a photo column divided/mirrored/repeated, 6 stages, softened 55/45 toward
                  the paper ×0.86) and the Steyerl size note (source size and enlargement on the page)
    techniques    two or three from the approved palette, at the approved strengths:
                  slit-scan amp 40 / period 22 (soft) or amp 140 / period 9 (bold); halation defaults;
                  matte 24/240 (hero) and 18/244 (prints); soft JPEG shadow ×1.16 at (−30, +24) or Ruff JPEG Q3
                  ×1.18; misregister 3 px; progressive blur; pixel stretch
    defamiliar    one device (round III: ostranenie), never several: the title's weight ramped 100→900 across
                  its letters, or the word cut on the page's own seam
    refinement    the final frame: running head top left, process line bottom left (two lines), folio bottom right,
                  a hairline rule, 40-56 px margins
"""
from __future__ import annotations

import numpy as np
from PIL import Image, ImageDraw

from ..artdirect import grain
from ..contemporary import halation, matte, richter_strip, ruff_jpeg, soft_jpeg
from ..defamiliar import misregister, slit_scan, text_mask
from ..defamiliar2 import pixel_stretch  # noqa: F401
from ..final import progressive_blur  # noqa: F401
from ..moodmachine import _face
from ..photo_led import tracked
from ..variants import fnt, width

RUNNING_HEAD = "FROM THE INSIDE  —  PART 2 MATCH"
INTER = ("thin", "xlight", "light", "regular", "bold", "black")          # Inter Display, 100 → 900


class Recipe:
    """Collects what a composer did, so the judge can check the recipe was followed."""

    def __init__(self):
        self.techniques, self.size_notes, self.strip, self.defamiliar, self.framed = [], 0, False, None, False
        self.title_boxes = []

    def used(self, name):
        if name not in self.techniques:
            self.techniques.append(name)

    def spec(self):
        return {"techniques": self.techniques, "size_notes": self.size_notes, "strip_title": self.strip,
                "defamiliar": self.defamiliar, "frame": self.framed, "title_boxes": self.title_boxes}

    # ------------------------------------------------------------- photo treatments (approved strengths)
    def hero(self, img, slit=None, bold=False, glow=True):
        if slit:
            x0, x1 = slit
            img = slit_scan(img, x0, x1, amp=140 if bold else 40, period=9 if bold else 22)
            self.used("slit-scan")
        if glow:
            img = halation(img)
            self.used("halation")
        self.used("matte")
        return matte(img, 24, 240)

    def print_(self, img):
        self.used("matte")
        return matte(img, 18, 244)

    def shadow(self, page, im, xy, paper, tone, kind="soft"):
        """The print over its own maximally compressed shadow (Ruff), at the approved size and offset."""
        x, y = xy
        if kind == "ruff":
            sh = ruff_jpeg(im.resize((int(im.size[0] * 1.18), int(im.size[1] * 1.18)), Image.LANCZOS), 4, 3)
        else:
            sh = soft_jpeg(im.resize((int(im.size[0] * 1.16), int(im.size[1] * 1.16)), Image.LANCZOS), paper, tone)
        page.paste(sh, (x - 30, y + 24))
        self.used("JPEG shadow")
        return (x - 30, y + 24, x - 30 + sh.size[0], y + 24 + sh.size[1])

    def misreg(self, img, dx=3):
        self.used("misregister")
        return misregister(img, dx, 0)

    # ------------------------------------------------------------- series DNA
    def strip_fill(self, src, col, w, h, paper, stages=6, mix=0.55, toward=None):
        """`toward`: the colour the stripes are softened toward (default the paper ×0.86, as approved); a dark
        page or a black stencil passes its own ink so the title keeps its contrast."""
        a = np.asarray(src.convert("RGB"), float)
        c = a[int(a.shape[0] * col[1]):int(a.shape[0] * col[2]), min(a.shape[1] - 1, int(a.shape[1] * col[0])), :]
        base = np.array(paper, float) * 0.86 if toward is None else np.array(toward, float)
        c = mix * c + (1 - mix) * base
        self.strip = True
        return richter_strip(c, w, h, stages=stages)

    def strip_title(self, page, text, font, xy, src, col, paper, tracking=10, rotate=0, mask=None, toward=None,
                    mix=0.55):
        """The title as a mask filled with the Richter strip; returns its box on the page."""
        size = font.size
        tw, th = int(width(text, font, tracking)) + 30, int(size * 1.25)
        m = mask if mask is not None else text_mask((tw, th), text, font, (0, -int(size * 0.12)), tracking)
        if rotate:
            m = m.rotate(rotate, expand=True)
        bb = m.getbbox()
        m = m.crop(bb)
        fill = self.strip_fill(src, col, m.size[0], m.size[1], paper, mix=mix, toward=toward)
        page.paste(fill, xy, m)
        box = (xy[0], xy[1], xy[0] + m.size[0], xy[1] + m.size[1])
        self.title_boxes.append(box)
        return box

    def note(self, d, xy, src_size, scale, fill, face="serif_it", extra=""):
        f = fnt(face, 15 if face == "serif_it" else 11)
        tracked(d, xy, f"{src_size[0]} × {src_size[1]}, ×{scale:.2f}{extra}", f, fill, 0.3)
        self.size_notes += 1

    # ------------------------------------------------------------- defamiliarization (one device)
    def ramp_mask(self, text, size, tracking=4):
        """The word with its weight stepped 100 → 900 across the letters (Inter Display)."""
        fonts = [fnt(INTER[min(len(INTER) - 1, round(i * (len(INTER) - 1) / max(1, len(text) - 1)))], size)
                 for i in range(len(text))]
        tw = int(sum(f.getlength(c) + tracking for f, c in zip(fonts, text))) + 30
        th = int(size * 1.25)
        m = Image.new("L", (tw, th), 0)
        d = ImageDraw.Draw(m)
        x = 0.0
        for f, c in zip(fonts, text):
            d.text((x, -int(size * 0.12)), c, font=f, fill=255)
            x += f.getlength(c) + tracking
        self.defamiliar = "weight ramp 100→900 across the title"
        return m

    def seam_mask(self, text, f_left, f_right, tracking=6):
        """The word cut on a vertical seam: its left half in one weight, its right half in another."""
        size = max(f_left.size, f_right.size)
        tw = int(max(width(text, f_left, tracking), width(text, f_right, tracking))) + 30
        th = int(size * 1.25)
        a = text_mask((tw, th), text, f_left, (0, -int(size * 0.12)), tracking)
        b = text_mask((tw, th), text, f_right, (0, -int(size * 0.12)), tracking)
        cut = int(width(text, f_left, tracking) / 2)
        m = a.copy()
        m.paste(b.crop((cut, 0, tw, th)), (cut, 0))
        self.defamiliar = "title cut on the splice seam: two weights joined at the centre line"
        return m

    # ------------------------------------------------------------- refinement: the final frame
    def frame(self, page, H, ink, rule, process, folio="11", head_fill=None, proc_fill=None, face="serif", px=40):
        d = ImageDraw.Draw(page)
        W = page.size[0]
        if face == "mono":
            fh, fp = fnt("mono", 12), fnt("mono", 12)
        else:
            fh, fp = _face("serif", "Light", 13), fnt("serif_it", 16)
        def auto(box):
            """ink on light ground, near-white on dark ground (measured under the line)"""
            lum = np.asarray(page.crop(box).convert("L"), float).mean()
            return ink if lum > 128 else (236, 234, 228)
        tracked(d, (40, 30), RUNNING_HEAD, fh, head_fill or auto((40, 28, 420, 48)), 2.4 if face != "mono" else 1.2)
        pfill = proc_fill or auto((px, H - 72, px + 560, H - 26))
        for i, ln in enumerate(process[:2]):
            tracked(d, (px, H - 70 + 24 * i), ln, fp, pfill, 0.3)
        tracked(d, (W - 76, H - 46), folio, _face("serif", "Light", 14), ink, 1)
        if rule:
            d.line([(1040, 40), (W - 40, 40)], fill=rule, width=1)
        self.framed = True


def finish(page, L, spec, R: Recipe, seed=12):
    return grain(page, 0.022, seed, size=1.5), {"layer": dict(L.__dict__), **spec, "recipe": R.spec()}
