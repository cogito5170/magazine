"""Evidence tracking for every proposed change (post-mortem requirement §4).

Rules
* A source is cited only if it is listed in ``SOURCES`` with its verification
  state; no paper title, clause, URL or number is generated ad hoc.
* ``claim_type`` separates official standards, empirical studies, measured
  facts, controlled preference tests and subjective hypotheses.
* A proposal is ``verified`` only if every supporting record is verified and
  its claim types can support the stated purpose; aesthetic purposes can
  only be supported by ``controlled_preference_test`` evidence.
"""
from __future__ import annotations

import datetime as dt
import json
import uuid
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class ClaimType(str, Enum):
    OFFICIAL_STANDARD = "official_standard"
    EMPIRICAL_STUDY = "empirical_study"
    MEASURED_FACT = "measured_fact"
    CONTROLLED_PREFERENCE_TEST = "controlled_preference_test"
    SUBJECTIVE_HYPOTHESIS = "subjective_hypothesis"


class Approval(str, Enum):
    NOT_REQUESTED = "not_requested"
    APPROVED = "approved"
    REJECTED = "rejected"


class Verification(str, Enum):
    VERIFIED = "verified"
    PARTIALLY_VERIFIED = "partially_verified"
    UNVERIFIED = "unverified"


class Purpose(str, Enum):
    FUNCTIONAL = "functional"      # legibility, contrast, clipping, file quality, information hierarchy
    AESTHETIC = "aesthetic"        # preference, style, beauty
    REFERENCE_MATCH = "reference_match"   # move toward a user-selected reference (not 'better')


class Source(BaseModel):
    source_id: str
    source_title: str
    source_url: Optional[str]
    publisher: Optional[str]
    publication_date: Optional[str]
    exact_section_or_page: Optional[str]
    source_scope: str
    applicability: str
    verification_status: Verification
    verification_note: str


# Only sources whose existence and content were checked in this project.
SOURCES: dict[str, Source] = {
    "wcag22_sc143": Source(
        source_id="wcag22_sc143",
        source_title="Web Content Accessibility Guidelines (WCAG) 2.2",
        source_url="https://www.w3.org/TR/WCAG22/",
        publisher="W3C",
        publication_date="2023-10-05 (W3C Recommendation)",
        exact_section_or_page="Success Criterion 1.4.3 Contrast (Minimum)",
        source_scope="Minimum luminance contrast ratio of text against its background for web content: "
                     "4.5:1, and 3:1 for large-scale text. It does not define aesthetic quality.",
        applicability="Normative for web content; for print or PDF portfolios it is a legibility reference, "
                      "not a binding requirement. Measured on the rendered PDF at the analysis resolution.",
        verification_status=Verification.PARTIALLY_VERIFIED,
        verification_note="Thresholds and publication date confirmed via secondary sources during development "
                          "(w3.org not reachable from the build environment); the 'large scale' point-size "
                          "definition was not re-checked against the W3C text."),
    "choi_hyun_2024": Source(
        source_id="choi_hyun_2024",
        source_title="Typeface network and the principle of font pairing",
        source_url="https://doi.org/10.1038/s41598-024-81601-w",
        publisher="Scientific Reports 14, 30820 (Springer Nature)",
        publication_date="2024-12",
        exact_section_or_page="abstract",
        source_scope="Morphological axes from font-use data (serif–sans, basic–decorative, light–bold) and "
                     "usage-network analysis of pairings. Describes usage patterns, not aesthetic truth.",
        applicability="Motivates the z_f descriptor axes. Latin-script usage data; generalisation to "
                      "Korean–Latin mixing is untested.",
        verification_status=Verification.PARTIALLY_VERIFIED,
        verification_note="Abstract-level content confirmed via search results (PMC11681221); full text not read."),
    "jiang_2018_vfp": Source(
        source_id="jiang_2018_vfp",
        source_title="Visual Font Pairing",
        source_url="https://arxiv.org/abs/1811.08015",
        publisher="arXiv (Jiang, Wang, Hertzmann, Jin, Fu)",
        publication_date="2018-11-19",
        exact_section_or_page="abstract",
        source_scope="Pairing learned from fonts co-occurring in PDFs; asymmetric pairing (header vs body).",
        applicability="Supports modelling pairings as asymmetric and learned from data; Latin-only.",
        verification_status=Verification.PARTIALLY_VERIFIED,
        verification_note="Abstract confirmed via search results; method details not read."),
    "taste_2026": Source(
        source_id="taste_2026",
        source_title="TASTE: A Designer-Annotated Multi-Dimensional Preference Dataset for AI-Generated "
                     "Graphic Design",
        source_url="https://arxiv.org/abs/2605.20731",
        publisher="arXiv (Zhu, Hirsch, Minetti, Nulty, Mehta)",
        publication_date="2026-05",
        exact_section_or_page="abstract",
        source_scope="Designers rate several criteria separately; single overall labels conflate axes; "
                     "automatic judges agree weakly with designers.",
        applicability="Supports separate criteria and caution about automatic aesthetic judges. Image "
                      "generation outputs, not Korean editorial layouts.",
        verification_status=Verification.PARTIALLY_VERIFIED,
        verification_note="Abstract-level content seen via search results; agreement numbers not verified."),
}


class Evidence(BaseModel):
    claim_type: ClaimType
    source_id: Optional[str] = None            # must be a key of SOURCES when given
    measurement_method: Optional[str] = None
    result: Any = None
    uncertainty: Optional[str] = None
    note: Optional[str] = None

    def source(self) -> Optional[Source]:
        if self.source_id is None:
            return None
        if self.source_id not in SOURCES:
            raise ValueError(f"unregistered source {self.source_id!r}: sources must not be invented")
        return SOURCES[self.source_id]

    def verification(self) -> Verification:
        if self.claim_type == ClaimType.SUBJECTIVE_HYPOTHESIS:
            return Verification.UNVERIFIED
        if self.claim_type == ClaimType.MEASURED_FACT:
            return Verification.VERIFIED if self.measurement_method and self.result is not None \
                else Verification.UNVERIFIED
        if self.claim_type == ClaimType.CONTROLLED_PREFERENCE_TEST:
            return Verification.VERIFIED if self.result is not None else Verification.UNVERIFIED
        s = self.source()
        return s.verification_status if s else Verification.UNVERIFIED


class ChangeProposal(BaseModel):
    proposal_id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    page: int                                  # 1-based
    element: str
    original_state: Any
    proposed_change: Any
    purpose: Purpose
    evidence: list[Evidence]
    preserved_strengths: list[str] = Field(default_factory=list)
    expected_tradeoffs: list[str] = Field(default_factory=list)
    user_approval_status: Approval = Approval.NOT_REQUESTED
    approval_record: Optional[dict] = None
    created: str = Field(default_factory=lambda: dt.datetime.now(dt.timezone.utc).isoformat())

    @property
    def verification_status(self) -> Verification:
        if not self.evidence:
            return Verification.UNVERIFIED
        states = [e.verification() for e in self.evidence]
        if self.purpose == Purpose.AESTHETIC and not any(
                e.claim_type == ClaimType.CONTROLLED_PREFERENCE_TEST and e.verification() == Verification.VERIFIED
                for e in self.evidence):
            return Verification.UNVERIFIED     # aesthetic claims need preference-test evidence
        if all(s == Verification.VERIFIED for s in states):
            return Verification.VERIFIED
        if any(s != Verification.UNVERIFIED for s in states):
            return Verification.PARTIALLY_VERIFIED
        return Verification.UNVERIFIED

    def flat(self) -> dict:
        """One flat record with all fields required by the post-mortem protocol."""
        src = [e.source() for e in self.evidence if e.source_id]
        return {
            "proposal_id": self.proposal_id, "page": self.page, "element": self.element,
            "original_state": self.original_state, "proposed_change": self.proposed_change,
            "purpose": self.purpose.value,
            "claim_type": [e.claim_type.value for e in self.evidence],
            "source_title": [s.source_title for s in src], "source_url": [s.source_url for s in src],
            "publisher": [s.publisher for s in src], "publication_date": [s.publication_date for s in src],
            "exact_section_or_page": [s.exact_section_or_page for s in src],
            "source_scope": [s.source_scope for s in src], "applicability": [s.applicability for s in src],
            "measurement_method": [e.measurement_method for e in self.evidence],
            "result": [e.result for e in self.evidence],
            "uncertainty": [e.uncertainty for e in self.evidence],
            "preserved_strengths": self.preserved_strengths, "expected_tradeoffs": self.expected_tradeoffs,
            "user_approval_status": self.user_approval_status.value,
            "verification_status": self.verification_status.value,
        }


def save_proposals(props: list[ChangeProposal], path: str) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        json.dump([p.model_dump(mode="json") for p in props], fh, ensure_ascii=False, indent=2)


def load_proposals(path: str) -> list[ChangeProposal]:
    with open(path, encoding="utf-8") as fh:
        return [ChangeProposal(**d) for d in json.load(fh)]


NORMATIVE = {ClaimType.OFFICIAL_STANDARD, ClaimType.EMPIRICAL_STUDY, ClaimType.CONTROLLED_PREFERENCE_TEST}


def is_actionable(p: ChangeProposal) -> tuple[bool, str]:
    """A change may be *proposed* only with a normative basis that is at least
    partially verified (official standard, empirical study, controlled
    preference test) or, for reference matching, the user's own choice of
    reference.  Everything else is reported as an observation only."""
    if p.purpose == Purpose.REFERENCE_MATCH:
        return True, "target is the user-selected reference (not a quality claim)"
    for e in p.evidence:
        if e.claim_type in NORMATIVE and e.verification() != Verification.UNVERIFIED:
            return True, f"normative basis: {e.claim_type.value} ({e.verification().value})"
    return False, "no verified normative basis: kept as an observation, not a change proposal"
