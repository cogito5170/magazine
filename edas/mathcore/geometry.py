"""Bounding-box geometry in the unified top-left page coordinate system (spec §2).

A box is (x0, y0, x1, y1) with x growing right and y growing down; the
spec's (x, y, w, h) form is x=x0, y=y0, w=x1-x0, h=y1-y0.
"""
from __future__ import annotations

from typing import Iterable, Optional, Sequence

import numpy as np

Box = tuple[float, float, float, float]


def xywh(b: Box) -> tuple[float, float, float, float]:
    return b[0], b[1], b[2] - b[0], b[3] - b[1]


def area(b: Box) -> float:
    return max(0.0, b[2] - b[0]) * max(0.0, b[3] - b[1])


def normalize_box(b: Box, W: float, H: float) -> Box:
    """(x/W, y/H, w/W, h/H) expressed as corner form."""
    return (b[0] / W, b[1] / H, b[2] / W, b[3] / H)


def clip_box(b: Box, W: float, H: float) -> Optional[Box]:
    c = (max(0.0, b[0]), max(0.0, b[1]), min(W, b[2]), min(H, b[3]))
    if c[2] <= c[0] or c[3] <= c[1]:
        return None
    return c


def intersect(a: Box, b: Box) -> Optional[Box]:
    c = (max(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), min(a[3], b[3]))
    if c[2] <= c[0] or c[3] <= c[1]:
        return None
    return c


def union_bbox(boxes: Iterable[Box]) -> Optional[Box]:
    boxes = list(boxes)
    if not boxes:
        return None
    a = np.asarray(boxes, dtype=float)
    return (float(a[:, 0].min()), float(a[:, 1].min()), float(a[:, 2].max()), float(a[:, 3].max()))


def union_area(boxes: Sequence[Box], clip: Optional[Box] = None) -> float:
    """Exact area of the union of axis-aligned rectangles (not the sum).

    Coordinate compression over x; in every x slab the covering y-intervals are
    merged.  O(n^2 log n), adequate for page-level object counts.
    """
    bs = []
    for b in boxes:
        if clip is not None:
            b = intersect(b, clip)
            if b is None:
                continue
        if b[2] > b[0] and b[3] > b[1]:
            bs.append(b)
    if not bs:
        return 0.0
    a = np.asarray(bs, dtype=float)
    xs = np.unique(np.concatenate([a[:, 0], a[:, 2]]))
    total = 0.0
    for xl, xr in zip(xs[:-1], xs[1:]):
        if xr <= xl:
            continue
        sel = a[(a[:, 0] <= xl) & (a[:, 2] >= xr)]
        if sel.size == 0:
            continue
        iv = sel[np.argsort(sel[:, 1])][:, [1, 3]]
        cov = 0.0
        cs, ce = iv[0]
        for s, e in iv[1:]:
            if s > ce:
                cov += ce - cs
                cs, ce = s, e
            else:
                ce = max(ce, e)
        cov += ce - cs
        total += cov * (xr - xl)
    return float(total)


def iou(a: Box, b: Box) -> float:
    """IoU = |A ∩ B| / |A ∪ B|; 0 when the union is empty."""
    i = intersect(a, b)
    ia = area(i) if i else 0.0
    u = area(a) + area(b) - ia
    return float(ia / u) if u > 0 else 0.0


def min_distance(a: Box, b: Box) -> float:
    """Shortest Euclidean distance between two closed rectangles (0 if they touch/overlap)."""
    dx = max(0.0, b[0] - a[2], a[0] - b[2])
    dy = max(0.0, b[1] - a[3], a[1] - b[3])
    return float(np.hypot(dx, dy))


def center(b: Box) -> tuple[float, float]:
    return (0.5 * (b[0] + b[2]), 0.5 * (b[1] + b[3]))


def union_area_in_cells(boxes: Sequence[Box], W: float, H: float, nx: int, ny: int) -> np.ndarray:
    """Covered fraction of each cell of an ny x nx partition of the page (exact)."""
    out = np.zeros((ny, nx))
    cw, ch = W / nx, H / ny
    for j in range(ny):
        for i in range(nx):
            cell = (i * cw, j * ch, (i + 1) * cw, (j + 1) * ch)
            out[j, i] = union_area(boxes, clip=cell) / (cw * ch)
    return out


def connected_box_groups(boxes: Sequence[Box], gap: float = 0.0) -> list[list[int]]:
    """Groups of boxes whose pairwise min distance <= gap (transitively)."""
    n = len(boxes)
    parent = list(range(n))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for i in range(n):
        for j in range(i + 1, n):
            if min_distance(boxes[i], boxes[j]) <= gap:
                ri, rj = find(i), find(j)
                if ri != rj:
                    parent[rj] = ri
    groups: dict[int, list[int]] = {}
    for i in range(n):
        groups.setdefault(find(i), []).append(i)
    return list(groups.values())
