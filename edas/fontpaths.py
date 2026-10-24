"""Locate font files the same way on Linux, macOS and Windows.

The approved spreads were rendered with the files bundled in ``edas/fontfiles`` (copies of the exact files),
so those are always tried first; user font folders are only a fallback.  No system path is required."""
from __future__ import annotations

import os

BUNDLED = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fontfiles")
USER_DIRS = [os.path.expanduser("~/.local/share/fonts"), os.path.expanduser("~/Library/Fonts"),
             os.path.expanduser("~/.fonts"), "/Library/Fonts", "/usr/share/fonts", "/usr/local/share/fonts",
             "C:/Windows/Fonts"]


def find(filename: str, sub: str | None = None) -> str:
    """Path of ``filename`` (optionally inside family folder ``sub``); the bundled copy when it exists."""
    bundled = os.path.join(BUNDLED, sub, filename) if sub else os.path.join(BUNDLED, filename)
    if os.path.exists(bundled):
        return bundled
    for root in USER_DIRS:
        if sub and os.path.exists(os.path.join(root, sub, filename)):
            return os.path.join(root, sub, filename)
        if not os.path.isdir(root):
            continue
        for d, _, files in os.walk(root):
            if filename in files:
                return os.path.join(d, filename)
    return bundled


def family_dir(sub: str, probe: str) -> str | None:
    """Folder holding a font family (e.g. ``pretendard``) or None."""
    p = find(probe, sub)
    return os.path.dirname(p) if os.path.exists(p) else None
