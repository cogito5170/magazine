"""Human preference data schema.

One ``Judgment`` = one rater's answer to one question for one A/B pair.
Criteria are separate labels and are never merged.  The experiment
(A_typeface vs B_page vs others) is part of every record so that typeface
preference and in-page preference are stored, modelled and validated
separately.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import uuid
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field, field_validator

# question wording shown to raters (Korean / English)
CRITERIA: dict[str, dict] = {
    "glyph_beauty": {"ko": "어느 서체 자체가 더 아름다운가?", "en": "Which typeface itself is more beautiful?",
                     "experiments": ["A_typeface"]},
    "sophistication": {"ko": "어느 서체가 더 세련되게 느껴지는가?", "en": "Which feels more sophisticated?",
                       "experiments": ["A_typeface", "B_page", "bilingual"]},
    "photo_fit": {"ko": "어느 서체가 사진과 더 잘 어울리는가?", "en": "Which fits the photograph better?",
                  "experiments": ["B_page"]},
    "portfolio_fit": {"ko": "어느 서체가 이 포트폴리오에 더 적합한가?", "en": "Which suits this portfolio better?",
                      "experiments": ["B_page"]},
    "readability": {"ko": "어느 쪽이 더 읽기 편한가?", "en": "Which is easier to read?",
                    "experiments": ["A_typeface", "B_page", "bilingual"]},
    "visual_harmony": {"ko": "한글과 영문이 시각적으로 더 조화로운 쪽은?", "en": "Which Korean–Latin pairing is more harmonious?",
                       "experiments": ["bilingual"]},
    "professionalism": {"ko": "어느 쪽이 더 전문적으로 보이는가?", "en": "Which looks more professional?",
                        "experiments": ["bilingual", "B_page"]},
    "target_style_fit": {"ko": "목표 스타일에 더 가까운 쪽은?", "en": "Which is closer to the target style?",
                         "experiments": ["bilingual", "B_page"]},
}
EXPERIMENTS = ("A_typeface", "B_page", "bilingual")
Choice = Literal["A", "B", "tie", "cannot_judge"]


class Judgment(BaseModel):
    judgment_id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    rater_id: str
    timestamp: str = Field(default_factory=lambda: dt.datetime.now(dt.timezone.utc).isoformat())
    experiment: str
    criterion: str
    stimulus_a: str
    stimulus_b: str
    choice: Choice
    font_a: Optional[str] = None
    font_b: Optional[str] = None
    page_id: Optional[str] = None          # e.g. "<pdf sha256>:p3" – used for leakage-safe splits
    project_id: Optional[str] = None
    target_style: Optional[str] = None
    presented_left: Optional[Literal["A", "B"]] = None
    rendering: dict[str, Any] = Field(default_factory=dict)
    response_ms: Optional[int] = None
    comment: Optional[str] = None

    @field_validator("criterion")
    @classmethod
    def _crit(cls, v):
        if v not in CRITERIA:
            raise ValueError(f"unknown criterion {v!r}; known: {sorted(CRITERIA)}")
        return v

    @field_validator("experiment")
    @classmethod
    def _exp(cls, v):
        if v not in EXPERIMENTS:
            raise ValueError(f"unknown experiment {v!r}")
        return v


class JudgmentStore:
    """Append-only JSON-lines store."""

    def __init__(self, path: str):
        self.path = path

    def append(self, j: Judgment) -> None:
        os.makedirs(os.path.dirname(os.path.abspath(self.path)), exist_ok=True)
        with open(self.path, "a", encoding="utf-8") as fh:
            fh.write(j.model_dump_json() + "\n")

    def extend(self, items) -> int:
        n = 0
        for it in items:
            self.append(it if isinstance(it, Judgment) else Judgment(**it))
            n += 1
        return n

    def load(self, experiment: Optional[str] = None, criterion: Optional[str] = None) -> list[Judgment]:
        if not os.path.exists(self.path):
            return []
        out = []
        with open(self.path, encoding="utf-8") as fh:
            for line in fh:
                if line.strip():
                    j = Judgment(**json.loads(line))
                    if (experiment is None or j.experiment == experiment) and \
                            (criterion is None or j.criterion == criterion):
                        out.append(j)
        return out


def json_schema() -> dict:
    return Judgment.model_json_schema()
