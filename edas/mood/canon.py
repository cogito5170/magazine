"""The canon: award-winning and canonical magazine pages as the reference the editor judges against.

The code judge (judge.py) measures invariants and distance from the approved moods; it cannot say whether a page is
good.  This module adds what the research says is needed for that (docs/canon/aesthetic_criteria.md):

    board        37 canonical designs (SPD, TDC, ADC, D&AD, European Design Awards, historical canon), 67 images,
                 every source opened and checked (docs/canon/board.json)
    nearest      the canonical pages closest to a candidate in colour and layout, shown beside it to the critic
    packet       candidate + nearest canon + criteria, written for a vision-language critic (a Claude session reads
                 prompt.md and writes critique.json); absolute grades per axis, never machine-vs-machine pairs
    critique     validated: one dominant device from DEVICES, a grade per axis, the canon page it is closest to
    editor pick  the user, as editor-in-chief, picks one page of a round; each pick becomes winner/loser rows in
                 docs/judgement_ledger.jsonl (edas.preference.bt can fit them once enough rows exist)
"""
from __future__ import annotations

import datetime as dt
import json
import os
import shutil

import numpy as np
from PIL import Image

from ..mathcore.color import rgb_to_lab

BOARD = "docs/canon/board.json"
CRITERIA = "docs/canon/aesthetic_criteria.md"
LEDGER = "docs/judgement_ledger.jsonl"

# the dominant devices observed on the 67 canonical pages (aesthetic_criteria.md §1), with board numbers
DEVICES = {
    "masthead-intrusion": (1, 19, 30, 9),
    "syllable-stack": (14, 28),
    "type-as-image": (11, 12, 13, 20, 26),
    "single-object": (5, 25, 17),
    "form-rhyme": (18, 16, 14),
    "text-as-texture": (10, 36, 27),
    "snapshot-classic-serif": (37, 35, 33),
}
GRADES = ("나쁨", "미흡", "보통", "좋음", "훌륭함")
AXES = ("device_clarity", "restraint", "type_hierarchy", "negative_space", "photo_crop",
        "familiar", "strange", "bold", "stable")


def board(path: str = BOARD) -> list[dict]:
    return json.load(open(path))


def descriptor(img: Image.Image) -> np.ndarray:
    """Colour layout (Lab on a 12×8 grid) plus edge density on the same grid: what a page looks like from across
    the room.  Pages are compared after fitting both to the same grid, so format differences matter little."""
    small = np.asarray(img.convert("RGB").resize((12, 8), Image.LANCZOS), float) / 255
    lab = rgb_to_lab(small).reshape(-1, 3) / np.array([100.0, 128.0, 128.0])
    g = np.asarray(img.convert("L").resize((96, 64), Image.LANCZOS), float) / 255
    edges = np.abs(np.diff(g, axis=0))[:, :-1] + np.abs(np.diff(g, axis=1))[:-1, :]
    e = np.array([edges[r * 8:(r + 1) * 8, c * 8:(c + 1) * 8].mean() for r in range(8) for c in range(12)])
    return np.concatenate([lab.ravel(), 4 * e])


def measures(img: Image.Image) -> dict:
    """Measured stand-ins for what a trained eye checks first, on a 24×16 grid of the page:
        quiet        share of cells with almost no edge energy (negative space, plain colour fields included)
        focal        number of separate high-energy regions (how many things compete for the first glance)
        palette      colours (3 bits per channel) that each cover >= 3% of the page"""
    g = np.asarray(img.convert("L").resize((480, 320), Image.LANCZOS), float) / 255
    edges = np.abs(np.diff(g, axis=0))[:, :-1] + np.abs(np.diff(g, axis=1))[:-1, :]
    cell = np.array([[edges[r * 20:(r + 1) * 20, c * 20:(c + 1) * 20].mean() for c in range(24)]
                     for r in range(15)])
    hot = cell > max(0.08, float(np.percentile(cell, 85)))
    seen, focal = np.zeros_like(hot), 0
    for r0, c0 in zip(*np.nonzero(hot)):
        if seen[r0, c0]:
            continue
        focal, stack = focal + 1, [(r0, c0)]
        while stack:
            r, c = stack.pop()
            if 0 <= r < hot.shape[0] and 0 <= c < hot.shape[1] and hot[r, c] and not seen[r, c]:
                seen[r, c] = True
                stack += [(r + 1, c), (r - 1, c), (r, c + 1), (r, c - 1)]
    q = (np.asarray(img.convert("RGB").resize((240, 160)), int) >> 5).reshape(-1, 3)
    _, counts = np.unique(q[:, 0] * 64 + q[:, 1] * 8 + q[:, 2], return_counts=True)
    return {"quiet": round(float((cell < 0.02).mean()), 3), "focal": int(focal),
            "palette": int((counts / counts.sum() >= 0.03).sum())}


def canon_ranges(items: list[dict] | None = None) -> dict:
    """10th-90th percentile of each measure over the canon images (photographed copies included, so the ranges
    are wide; they are evidence for the critic, not an invariant)."""
    items = items if items is not None else board()
    ms = [measures(Image.open(im["file"])) for it in items for im in it.get("images", []) if os.path.exists(im["file"])]
    return {k: [float(np.percentile([m[k] for m in ms], 10)), float(np.percentile([m[k] for m in ms], 90))]
            for k in ("quiet", "focal", "palette")}


def zooms(page: Image.Image, boxes: list, out: str) -> list[str]:
    """2× crops of the display type and of the gutter: the detail a downscaled page hides (kerning, stroke
    contrast, the cut at the seam).  Visual prompting with zoomed patches improves VLM critique (Duan et al. 2024)."""
    names, w, h = [], *page.size
    regions = [("zoom_title", b) for b in boxes[:2]] + [("zoom_gutter", (w // 2 - w // 10, 0, w // 2 + w // 10, h))]
    for i, (name, (x0, y0, x1, y1)) in enumerate(regions):
        pad = 24
        crop = page.crop((max(0, x0 - pad), max(0, y0 - pad), min(w, x1 + pad), min(h, y1 + pad)))
        crop = crop.resize((crop.width * 2, crop.height * 2), Image.LANCZOS)
        fn = f"{name}_{i + 1}.jpg" if name == "zoom_title" else f"{name}.jpg"
        crop.convert("RGB").save(os.path.join(out, fn), quality=90)
        names.append(fn)
    return names


def nearest(page: Image.Image, k: int = 3, items: list[dict] | None = None, exclude: int | None = None) -> list[dict]:
    """The k canonical images closest to the page (Euclidean distance between descriptors), one per design.
    `exclude` leaves one board item out (leave-one-out validation: a canon page must not be shown itself)."""
    items = [it for it in (items if items is not None else board()) if it["index"] != exclude]
    d0 = descriptor(page)
    scored = []
    for it in items:
        best = None
        for im in it.get("images", []):
            if not os.path.exists(im["file"]):
                continue
            dist = float(np.linalg.norm(descriptor(Image.open(im["file"])) - d0))
            if best is None or dist < best[0]:
                best = (dist, im["file"])
        if best:
            scored.append({"index": it["index"], "publication": it["publication"], "issue": it["issue"],
                           "award": it["award"], "file": best[1], "distance": round(best[0], 3)})
    return sorted(scored, key=lambda s: s["distance"])[:k]


PROMPT = """# 원칙 비평 요청

당신은 편집 디자인 심사위원이다. `candidate.jpg`는 심사할 시안이다. `canon_*.jpg`는 정전 보드에서 색과 배치가 가장
가까운 지면이며, 각 파일의 출처와 수상은 아래 표에 있다. 판정 기준은 `aesthetic_criteria.md`다. 먼저 읽고 판정한다.

{refs}

작가가 밝힌 주도 장치: {device}

확대 이미지 (축소된 지면에서 사라지는 디테일: 커닝, 획 대비, 거터의 절단): {zooms}

측정값 (시안 / 정전 이미지의 10~90 백분위). quiet는 네거티브 스페이스와 단색 면의 비율, focal은 첫 시선을 다투는
영역의 수, palette는 면적 3% 이상인 색의 수다. 범위를 벗어난 값은 근거로 쓰되, 정전 사진에는 촬영 배경이 섞여 있어
범위는 넓게 잡혀 있다.

{measures}

규칙
- 시안을 정전과 나란히 놓고 본다. 비교 없이 등급을 매기지 않는다.
- 축마다 독립된 절대 등급을 매긴다: {grades}.
- 주도 장치가 둘 이상 경쟁하면 device_clarity와 restraint를 낮춘다.
- 근거는 지면에서 보이는 것만 쓴다 (그리드, 단 구성, 스케일 대비, 획 대비, 여백, 크롭, 블리드, 팔레트).
- 확대 이미지에서 조판 결함(커닝, 행간, 획이 잘린 곳, 거터에 먹힌 글자)을 찾으면 evidence에 적고 type_hierarchy를 낮춘다.

`critique_<심사자 이름>.json`(예: critique_claude.json, critique_gpt.json)에 다음 형식으로만 쓴다:

```json
{{"dominant_device": "<{devices} 중 하나, 또는 none>",
  "grades": {{{axes}}},
  "closest_canon": <보드 번호>,
  "evidence": "<지면에서 본 근거, 2~4문장>",
  "verdict": "pass | revise | reject"}}
```
"""


RANGES = "docs/canon/measures.json"


def write_packet(page: Image.Image, folder: str, device: str | None = None, k: int = 3,
                 title_boxes: list | None = None, exclude: int | None = None) -> dict:
    """Write candidate, zoomed crops, nearest canon images, measures, criteria and prompt into <folder>/critic/."""
    out = os.path.join(folder, "critic")
    os.makedirs(out, exist_ok=True)
    page.convert("RGB").save(os.path.join(out, "candidate.jpg"), quality=90)
    zs = zooms(page, title_boxes or [], out)
    m = measures(page)
    rng = json.load(open(RANGES)) if os.path.exists(RANGES) else canon_ranges()
    mrows = ["| 측정 | 시안 | 정전 10~90% |", "| --- | --- | --- |"] + \
        [f"| {key} | {m[key]} | {rng[key][0]:g}–{rng[key][1]:g} |" for key in ("quiet", "focal", "palette")]
    refs = nearest(page, k, exclude=exclude)
    rows = ["| 파일 | 보드 번호 | 매체 | 호 | 수상 |", "| --- | --- | --- | --- | --- |"]
    for i, r in enumerate(refs, 1):
        name = f"canon_{i}.jpg"
        shutil.copyfile(r["file"], os.path.join(out, name))
        rows.append(f"| {name} | {r['index']} | {r['publication']} | {r['issue']} | {r['award']} |")
    shutil.copyfile(CRITERIA, os.path.join(out, "aesthetic_criteria.md"))
    prompt = PROMPT.format(refs="\n".join(rows), device=device or "(밝히지 않음)", grades=" / ".join(GRADES),
                           zooms=", ".join(zs), measures="\n".join(mrows),
                           devices=", ".join(DEVICES), axes=", ".join(f'"{a}": "<등급>"' for a in AXES))
    open(os.path.join(out, "prompt.md"), "w").write(prompt)
    return {"packet": out, "nearest": [r["index"] for r in refs], "measures": m}


def validate_critique(c: dict) -> list[str]:
    """Problems with a critic's answer; empty when it can be recorded."""
    errs = []
    if c.get("dominant_device") not in (*DEVICES, "none"):
        errs.append(f"dominant_device must be one of {', '.join(DEVICES)} or none")
    g = c.get("grades") or {}
    missing = [a for a in AXES if a not in g]
    if missing:
        errs.append("grades missing: " + ", ".join(missing))
    bad = [a for a, v in g.items() if a in AXES and v not in GRADES]
    if bad:
        errs.append("grades not in the scale: " + ", ".join(bad))
    if not isinstance(c.get("closest_canon"), int) or not 1 <= c["closest_canon"] <= len(board()):
        errs.append("closest_canon must be a board number")
    if not str(c.get("evidence", "")).strip():
        errs.append("evidence is empty")
    if c.get("verdict") not in ("pass", "revise", "reject"):
        errs.append("verdict must be pass, revise or reject")
    return errs


def critic_passes(c: dict) -> bool:
    """pass, a named device, and no axis below 보통 on device clarity, restraint, familiar or stable."""
    floor = GRADES.index("보통")
    keys = ("device_clarity", "restraint", "familiar", "stable")
    return c.get("verdict") == "pass" and c.get("dominant_device") != "none" and \
        all(GRADES.index(c["grades"][a]) >= floor for a in keys)


def device_check(spec: dict) -> bool | None:
    """A writer's card that names a dominant device must name one from the canon; None when it names none."""
    d = spec.get("dominant_device")
    return None if d is None else d in DEVICES


def editor_pick(round_id: str, shown: list[str], chosen: str | None, reason: str = "",
                ledger: str = LEDGER) -> list[dict]:
    """The editor-in-chief picked `chosen` out of `shown` (or none of them).  One row per loser; a round with no
    pick is recorded as one row with winner null, so 'all rejected' is data too."""
    if chosen is not None and chosen not in shown:
        raise ValueError(f"{chosen!r} was not among the pages shown")
    at = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    if chosen is None:
        rows = [{"round": round_id, "winner": None, "loser": None, "shown": shown, "reason": reason, "at": at}]
    else:
        rows = [{"round": round_id, "winner": chosen, "loser": x, "shown": shown, "reason": reason, "at": at}
                for x in shown if x != chosen]
    with open(ledger, "a") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    return rows


# ----------------------------------------------------------------------------------------------- ensemble
# A single off-the-shelf VLM judge agrees with the designer majority less than 55% of the time (TASTE, 2026), and
# LLM judges flip under distractors (Tripathi et al., COLM 2025).  So the final word is an ensemble of independent
# critics with absolute grades, aggregated by the median, and the ensemble must agree before it may accept.

KEY_AXES = ("device_clarity", "restraint", "familiar", "stable")
MIN_CRITICS = 2
MAX_SPREAD = 1          # on a key axis the critics may differ by at most one step of the scale


def qwk(a: list[int], b: list[int], n: int = len(GRADES)) -> float:
    """Quadratic weighted Cohen's kappa between two raters' ordinal grades (1 = perfect, 0 = chance)."""
    a, b = np.asarray(a), np.asarray(b)
    o = np.zeros((n, n))
    for x, y in zip(a, b):
        o[x, y] += 1
    w = np.array([[(i - j) ** 2 / (n - 1) ** 2 for j in range(n)] for i in range(n)])
    e = np.outer(o.sum(1), o.sum(0)) / max(o.sum(), 1)
    den = (w * e).sum()
    return 1.0 if den == 0 else float(1 - (w * o).sum() / den)


def aggregate(critiques: dict[str, dict]) -> dict:
    """Median grade per axis over valid critiques; pass only with >= MIN_CRITICS critics, a pass by majority,
    key axes at 보통 or better, a named device agreed by the majority, and key-axis spread <= MAX_SPREAD."""
    ok = {k: c for k, c in critiques.items() if not validate_critique(c)}
    idx = {k: [GRADES.index(c["grades"][a]) for a in AXES] for k, c in ok.items()}
    names = sorted(idx)
    if not names:
        return {"n": 0, "verdict": "fail", "why": "no valid critique"}
    med = {a: GRADES[int(np.floor(np.median([idx[k][i] for k in names])))] for i, a in enumerate(AXES)}
    spread = {a: int(np.ptp([idx[k][AXES.index(a)] for k in names])) for a in KEY_AXES}
    devices = [ok[k]["dominant_device"] for k in names]
    device = max(set(devices), key=devices.count)
    passes = sum(ok[k]["verdict"] == "pass" for k in names)
    pair = [qwk(idx[x], idx[y]) for i, x in enumerate(names) for y in names[i + 1:]]
    why = []
    if len(names) < MIN_CRITICS:
        why.append(f"{len(names)} critic(s) < {MIN_CRITICS}")
    if passes * 2 <= len(names):
        why.append(f"pass by {passes} of {len(names)}")
    if device == "none" or devices.count(device) * 2 <= len(names):
        why.append(f"no agreed dominant device ({', '.join(devices)})")
    low = [a for a in KEY_AXES if GRADES.index(med[a]) < GRADES.index("보통")]
    if low:
        why.append("below 보통: " + ", ".join(low))
    wide = [a for a, v in spread.items() if v > MAX_SPREAD]
    if wide:
        why.append("critics disagree on " + ", ".join(wide))
    return {"n": len(names), "critics": names, "grades": med, "device": device, "spread": spread,
            "agreement_qwk": round(float(np.mean(pair)), 3) if pair else None,
            "verdict": "fail" if why else "pass", "why": "; ".join(why) or "ensemble agrees"}


# ---------------------------------------------------------------------------------------------- validation
# The judge is validated before it is trusted: canonical pages (left out of their own references) and the
# approved spreads are positives; drafts the user rejected are negatives.  Reported as balanced accuracy and
# ROC AUC of the mean key-axis grade, so a judge that passes everything or nothing scores 0.5.

def score(agg: dict) -> float:
    return float(np.mean([GRADES.index(agg["grades"][a]) for a in KEY_AXES])) if agg.get("grades") else 0.0


def roc_auc(pos: list[float], neg: list[float]) -> float:
    """Probability that a positive scores above a negative (ties count half): Mann-Whitney U / (n_pos n_neg)."""
    if not pos or not neg:
        return float("nan")
    wins = sum((p > n) + 0.5 * (p == n) for p in pos for n in neg)
    return wins / (len(pos) * len(neg))


def validation_report(results: list[tuple[int, dict]]) -> dict:
    """results: (label 1/0, aggregate) pairs."""
    pos = [r for y, r in results if y == 1]
    neg = [r for y, r in results if y == 0]
    tpr = np.mean([r["verdict"] == "pass" for r in pos]) if pos else float("nan")
    tnr = np.mean([r["verdict"] != "pass" for r in neg]) if neg else float("nan")
    qs = [r["agreement_qwk"] for _, r in results if r.get("agreement_qwk") is not None]
    return {"n_pos": len(pos), "n_neg": len(neg), "tpr": round(float(tpr), 3), "tnr": round(float(tnr), 3),
            "balanced_accuracy": round(float((tpr + tnr) / 2), 3),
            "auc": round(roc_auc([score(r) for r in pos], [score(r) for r in neg]), 3),
            "mean_agreement_qwk": round(float(np.mean(qs)), 3) if qs else None}
