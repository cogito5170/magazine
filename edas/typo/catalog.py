"""Installed-font catalogue: availability, coverage and licence metadata.

Reads the sfnt tables directly (no fontTools dependency):
* ``name``  – family (1/16), subfamily (2/17), licence description (13), licence URL (14)
* ``OS/2``  – usWeightClass, fsType (embedding permissions)
* ``cmap``  – Unicode coverage (formats 4 and 12)
Licence fields are reported exactly as stored in the font; when absent the
licence is "unknown" (it is never guessed).
"""
from __future__ import annotations

import os
import struct
from dataclasses import dataclass, field
from typing import Optional

FONT_DIRS = ["/usr/share/fonts", "/usr/local/share/fonts", os.path.expanduser("~/.fonts"),
             os.path.expanduser("~/.local/share/fonts"), "/Library/Fonts", "C:/Windows/Fonts"]

_FSTYPE = {0: "installable", 2: "restricted (no embedding)", 4: "preview & print", 8: "editable"}


@dataclass
class FontFace:
    path: str
    index: int
    family: str
    subfamily: str
    full_name: str
    weight_class: Optional[int]
    fs_type: Optional[int]
    license: Optional[str]
    license_url: Optional[str]
    ranges: list = field(default_factory=list)   # [(start, end)] inclusive

    def covers(self, cp: int) -> bool:
        lo, hi = 0, len(self.ranges) - 1
        while lo <= hi:
            m = (lo + hi) // 2
            s, e = self.ranges[m]
            if cp < s:
                hi = m - 1
            elif cp > e:
                lo = m + 1
            else:
                return True
        return False

    def coverage(self, text: str) -> float:
        cps = {ord(c) for c in text if not c.isspace()}
        if not cps:
            return 1.0
        return sum(self.covers(c) for c in cps) / len(cps)

    @property
    def embedding(self) -> str:
        if self.fs_type is None:
            return "unknown"
        if self.fs_type == 0:
            return _FSTYPE[0]
        bits = [v for k, v in _FSTYPE.items() if k and self.fs_type & k]
        return ", ".join(bits) or f"fsType={self.fs_type}"

    def to_dict(self) -> dict:
        return {"path": self.path, "index": self.index, "family": self.family, "subfamily": self.subfamily,
                "full_name": self.full_name, "weight_class": self.weight_class, "embedding": self.embedding,
                "license": self.license or "unknown", "license_url": self.license_url,
                "hangul_syllables_covered": sum(max(0, min(e, 0xD7A3) - max(s, 0xAC00) + 1)
                                                for s, e in self.ranges)}


def _tables(data: bytes, off: int) -> dict:
    n = struct.unpack(">H", data[off + 4: off + 6])[0]
    t = {}
    for i in range(n):
        tag, _, o, ln = struct.unpack(">4sIII", data[off + 12 + 16 * i: off + 28 + 16 * i])
        t[tag.decode("latin-1")] = (o, ln)
    return t


def _names(data: bytes, o: int) -> dict:
    _, count, so = struct.unpack(">HHH", data[o: o + 6])
    best: dict[int, tuple[int, str]] = {}
    for i in range(count):
        pid, eid, lid, nid, ln, off = struct.unpack(">HHHHHH", data[o + 6 + 12 * i: o + 18 + 12 * i])
        raw = data[o + so + off: o + so + off + ln]
        if pid == 3 or pid == 0:
            s = raw.decode("utf-16-be", "replace")
            rank = 0 if lid == 0x409 else 1
        elif pid == 1:
            s = raw.decode("latin-1", "replace")
            rank = 2
        else:
            continue
        if nid not in best or rank < best[nid][0]:
            best[nid] = (rank, s)
    return {k: v[1] for k, v in best.items()}


def _cmap(data: bytes, o: int) -> list:
    _, n = struct.unpack(">HH", data[o: o + 4])
    subs = []
    for i in range(n):
        pid, eid, off = struct.unpack(">HHI", data[o + 4 + 8 * i: o + 12 + 8 * i])
        subs.append((pid, eid, o + off))
    pref = sorted(subs, key=lambda s: {(3, 10): 0, (0, 4): 1, (0, 6): 1, (3, 1): 2, (0, 3): 3}.get((s[0], s[1]), 9))
    for pid, eid, so in pref:
        fmt = struct.unpack(">H", data[so: so + 2])[0]
        if fmt == 12:
            ng = struct.unpack(">I", data[so + 12: so + 16])[0]
            rs = [struct.unpack(">III", data[so + 16 + 12 * i: so + 28 + 12 * i])[:2] for i in range(ng)]
            return _merge(rs)
        if fmt == 4:
            segx2 = struct.unpack(">H", data[so + 6: so + 8])[0]
            seg = segx2 // 2
            ends = struct.unpack(f">{seg}H", data[so + 14: so + 14 + segx2])
            starts = struct.unpack(f">{seg}H", data[so + 16 + segx2: so + 16 + 2 * segx2])
            return _merge([(s, e) for s, e in zip(starts, ends) if s != 0xFFFF])
    return []


def _merge(rs):
    rs = sorted(rs)
    out = []
    for s, e in rs:
        if out and s <= out[-1][1] + 1:
            out[-1] = (out[-1][0], max(out[-1][1], e))
        else:
            out.append((s, e))
    return out


def read_faces(path: str) -> list[FontFace]:
    with open(path, "rb") as fh:
        data = fh.read()
    if data[:4] == b"ttcf":
        n = struct.unpack(">I", data[8:12])[0]
        offs = list(struct.unpack(f">{n}I", data[12: 12 + 4 * n]))
    else:
        offs = [0]
    faces = []
    for idx, off in enumerate(offs):
        t = _tables(data, off)
        nm = _names(data, t["name"][0]) if "name" in t else {}
        wc = fs = None
        if "OS/2" in t:
            o = t["OS/2"][0]
            wc, fs = struct.unpack(">HH", data[o + 4: o + 8])
        faces.append(FontFace(path=path, index=idx, family=nm.get(16) or nm.get(1, ""),
                              subfamily=nm.get(17) or nm.get(2, ""), full_name=nm.get(4, ""),
                              weight_class=wc, fs_type=fs, license=nm.get(13), license_url=nm.get(14),
                              ranges=_cmap(data, t["cmap"][0]) if "cmap" in t else []))
    return faces


def scan_system_fonts(dirs: Optional[list[str]] = None) -> list[FontFace]:
    faces = []
    for d in dirs or FONT_DIRS:
        if not os.path.isdir(d):
            continue
        for root, _, files in os.walk(d):
            for f in sorted(files):
                if f.lower().endswith((".ttf", ".otf", ".ttc")):
                    try:
                        faces.extend(read_faces(os.path.join(root, f)))
                    except Exception:
                        continue
    return faces
