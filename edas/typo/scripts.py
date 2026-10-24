"""Unicode script classes and Hangul syllable structure."""
from __future__ import annotations

import unicodedata

CLASSES = ("hangul", "hangul_jamo", "latin_upper", "latin_lower", "digit", "punct", "han", "kana",
           "space", "other")

# vowel index (0..20) of a precomposed syllable: ㅏㅐㅑㅒㅓㅔㅕㅖㅗㅘㅙㅚㅛㅜㅝㅞㅟㅠㅡㅢㅣ
_VERTICAL = {0, 1, 2, 3, 4, 5, 6, 7, 20}     # vowel to the right of the initial
_HORIZONTAL = {8, 12, 13, 17, 18}            # vowel below the initial
_COMPOUND = {9, 10, 11, 14, 15, 16, 19}      # vowel both below and right
_DOUBLE_INITIAL = {1, 4, 8, 10, 13}          # ㄲ ㄸ ㅃ ㅆ ㅉ
_DOUBLE_FINAL = {2, 3, 5, 6, 9, 10, 11, 12, 13, 14, 15, 18, 20}


def char_class(ch: str) -> str:
    cp = ord(ch)
    if ch.isspace():
        return "space"
    if 0xAC00 <= cp <= 0xD7A3:
        return "hangul"
    if 0x1100 <= cp <= 0x11FF or 0x3130 <= cp <= 0x318F or 0xA960 <= cp <= 0xA97F or 0xD7B0 <= cp <= 0xD7FF:
        return "hangul_jamo"
    cat = unicodedata.category(ch)
    if cat == "Nd":
        return "digit"
    if cat.startswith("L") and (cp < 0x0250 or 0x1E00 <= cp <= 0x1EFF or 0xFF21 <= cp <= 0xFF5A):
        return "latin_upper" if ch.isupper() else "latin_lower"
    if 0x4E00 <= cp <= 0x9FFF or 0x3400 <= cp <= 0x4DBF:
        return "han"
    if 0x3040 <= cp <= 0x30FF:
        return "kana"
    if cat[0] in "PS":
        return "punct"
    return "other"


def script_group(cls: str) -> str:
    """K (Korean), E (Latin letters), D (digits), P (punctuation), O (other)."""
    if cls in ("hangul", "hangul_jamo"):
        return "K"
    if cls in ("latin_upper", "latin_lower"):
        return "E"
    if cls == "digit":
        return "D"
    if cls == "punct":
        return "P"
    return "O"


def hangul_structure(ch: str) -> dict | None:
    """Decompose a precomposed syllable: indices, shape type 1..6 and component count.

    Shape types (standard 6-way classification):
      1 vertical vowel, no final      4 vertical vowel + final
      2 horizontal vowel, no final    5 horizontal vowel + final
      3 compound vowel, no final      6 compound vowel + final
    Component count = number of basic jamo shapes (double consonants,
    compound vowels and cluster finals count 2).
    """
    cp = ord(ch)
    if not 0xAC00 <= cp <= 0xD7A3:
        return None
    s = cp - 0xAC00
    L, V, T = s // 588, (s % 588) // 28, s % 28
    shape = 0 if V in _VERTICAL else (1 if V in _HORIZONTAL else 2)
    stype = shape + 1 + (3 if T else 0)
    comps = (2 if L in _DOUBLE_INITIAL else 1) + (2 if V in _COMPOUND else 1)
    if T:
        comps += 2 if T in _DOUBLE_FINAL else 1
    return {"L": L, "V": V, "T": T, "type": stype, "has_final": bool(T), "components": comps}
