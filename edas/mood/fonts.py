"""Fonts used by the mood spreads, all under the SIL Open Font License 1.1.  Both families are bundled in
edas/fontfiles, so ``install`` is only needed when that folder was removed; missing fonts would fall back
silently in rendering (Pretendard → WenQuanYi, Noto Serif KR → Caladea)."""
from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import zipfile

from ..fontpaths import family_dir

ROOT = os.path.expanduser("~/.local/share/fonts")
FONTS = {
    "pretendard": {
        "url": "https://github.com/orioncactus/pretendard/releases/download/v1.3.9/Pretendard-1.3.9.zip",
        "members": [f"public/static/Pretendard-{w}.otf" for w in
                    ("Thin", "ExtraLight", "Light", "Regular", "Medium", "SemiBold", "Bold", "ExtraBold", "Black")]
                   + ["LICENSE.txt"],
        "probe": "Pretendard-Regular.otf"},
    "notoserifkr": {
        "url": "https://github.com/notofonts/noto-cjk/releases/download/Serif2.003/13_NotoSerifKR.zip",
        "members": [f"SubsetOTF/KR/NotoSerifKR-{w}.otf" for w in
                    ("ExtraLight", "Light", "Regular", "Medium", "SemiBold")] + ["LICENSE"],
        "probe": "NotoSerifKR-Regular.otf"},
}


def status() -> dict[str, bool]:
    return {k: family_dir(k, v["probe"]) is not None for k, v in FONTS.items()}


def install(names=None) -> list[str]:
    done = []
    for k in names or FONTS:
        spec = FONTS[k]
        dest = os.path.join(ROOT, k)
        os.makedirs(dest, exist_ok=True)
        with tempfile.TemporaryDirectory() as tmp:
            z = os.path.join(tmp, "f.zip")
            if shutil.which("curl"):
                subprocess.run(["curl", "-sSfL", "-o", z, spec["url"]], check=True)
            else:
                import urllib.request
                urllib.request.urlretrieve(spec["url"], z)
            with zipfile.ZipFile(z) as zf:
                for m in spec["members"]:
                    with zf.open(m) as fh, open(os.path.join(dest, os.path.basename(m)), "wb") as out:
                        shutil.copyfileobj(fh, out)
        done.append(dest)
    return done
