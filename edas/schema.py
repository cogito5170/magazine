"""Common data schema (spec §1, §14).

Every parameter has a specification ``ParameterSpec`` holding the eight
attributes p_i = (D, U, F, N, T, E, C, V) plus its domain, missing-value
policy and measurement type.  Every computed value is emitted as a
``ParameterResult`` that follows the output schema of spec §14.

Rules enforced here:
* unmeasured values are ``None`` (JSON ``null``) – never filled in;
* NaN / inf are converted to ``None`` and the reason is recorded;
* a ``direct`` parameter computed from a raster estimate is downgraded to
  ``estimated`` (spec §12).
"""
from __future__ import annotations

import math
from enum import Enum
from typing import Any, Optional

import numpy as np
from pydantic import BaseModel, Field

METHOD_VERSION = "edas-0.1.0"


class MeasurementType(str, Enum):
    DIRECT = "direct"          # 측정값: computed exactly from PDF objects / pixels
    ESTIMATED = "estimated"    # 추정값: heuristic or model-free estimator, raster segmentation
    PREDICTED = "predicted"    # 학습 기반 예측값: requires a trained model


class Status(str, Enum):
    MEASURED = "measured"
    ESTIMATED = "estimated"
    PREDICTED = "predicted"
    NOT_MEASURED = "not_measured"            # no capability / input to measure
    NOT_COMPUTABLE = "not_computable"        # required input missing (e.g. original image)
    UNDEFINED = "undefined"                  # mathematically undefined (0 denominator, N<2 ...)
    INSUFFICIENT_DATA = "insufficient_data"  # computable but statistically unreliable
    NO_REFERENCE = "no_reference"            # needs a reference profile
    NO_MODEL = "no_model"                    # needs trained model / labelled data


class ErrorKind(str, Enum):
    TWO_SIDED = "two_sided"
    MIN = "min"      # value should be >= t
    MAX = "max"      # value should be <= t
    NONE = "none"    # no target defined: report measurement only


class ParameterSpec(BaseModel):
    parameter_id: str
    name: str
    module: str
    definition: str                       # D
    unit: str                             # U
    formula: str                          # F
    normalization: str = "none"           # N
    target: str = "reference_profile"     # T  (how the target is obtained)
    error_kind: ErrorKind = ErrorKind.NONE  # E
    confidence: str = "deterministic"     # C
    validation: str = "unit test on synthetic PDF with known answer"  # V
    measurement_type: MeasurementType = MeasurementType.DIRECT
    domain: str = "R"
    missing: str = "null when inputs are absent"
    scope: str = "page"                   # page | document | both
    notes: list[str] = Field(default_factory=list)


class ParameterResult(BaseModel):
    parameter_id: str
    name: str
    value: Any = None
    unit: str
    measurement_type: MeasurementType
    formula: str
    target: Any = None
    tolerance: Optional[float] = None
    error: Optional[float] = None
    confidence: Any = None
    validation_status: Status = Status.NOT_MEASURED
    method_version: Optional[str] = METHOD_VERSION
    scope: str = "page"
    page_index: Optional[int] = None
    source: Optional[str] = None          # pdf_objects | raster | derived | model
    details: dict[str, Any] = Field(default_factory=dict)
    notes: list[str] = Field(default_factory=list)

    def scalar(self) -> Optional[float]:
        v = self.value
        if isinstance(v, bool):
            return float(v)
        if isinstance(v, (int, float)):
            return float(v)
        return None


# --------------------------------------------------------------------------
# JSON hygiene
# --------------------------------------------------------------------------

def jsonable(x: Any) -> Any:
    """Convert numpy containers/scalars to plain Python; NaN/inf -> None."""
    if x is None or isinstance(x, (str, bool)):
        return x
    if isinstance(x, (np.bool_,)):
        return bool(x)
    if isinstance(x, (int, np.integer)):
        return int(x)
    if isinstance(x, (float, np.floating)):
        f = float(x)
        return f if math.isfinite(f) else None
    if isinstance(x, np.ndarray):
        return jsonable(x.tolist())
    if isinstance(x, dict):
        return {str(k): jsonable(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [jsonable(v) for v in x]
    if isinstance(x, Enum):
        return x.value
    if isinstance(x, BaseModel):
        return jsonable(x.model_dump())
    return x


def _has_nonfinite(x: Any) -> bool:
    if isinstance(x, (float, np.floating)):
        return not math.isfinite(float(x))
    if isinstance(x, np.ndarray):
        return x.dtype.kind == "f" and not np.all(np.isfinite(x))
    if isinstance(x, dict):
        return any(_has_nonfinite(v) for v in x.values())
    if isinstance(x, (list, tuple)):
        return any(_has_nonfinite(v) for v in x)
    return False


_STATUS_FOR_TYPE = {
    MeasurementType.DIRECT: Status.MEASURED,
    MeasurementType.ESTIMATED: Status.ESTIMATED,
    MeasurementType.PREDICTED: Status.PREDICTED,
}


def make_result(
    spec: ParameterSpec,
    value: Any,
    *,
    status: Optional[Status] = None,
    source: Optional[str] = None,
    page_index: Optional[int] = None,
    scope: Optional[str] = None,
    details: Optional[dict] = None,
    notes: Optional[list[str]] = None,
    confidence: Any = None,
    measurement_type: Optional[MeasurementType] = None,
) -> ParameterResult:
    notes = list(notes or [])
    mtype = measurement_type or spec.measurement_type
    if source == "raster" and mtype == MeasurementType.DIRECT:
        mtype = MeasurementType.ESTIMATED
        notes.append("computed from raster segmentation, not from PDF objects")
    if _has_nonfinite(value):
        notes.append("non-finite components replaced by null")
    value = jsonable(value)
    if value is None and status is None:
        status = Status.NOT_MEASURED
    if status is None:
        status = _STATUS_FOR_TYPE[mtype]
    return ParameterResult(
        parameter_id=spec.parameter_id,
        name=spec.name,
        value=value,
        unit=spec.unit,
        measurement_type=mtype,
        formula=spec.formula,
        validation_status=status,
        scope=scope or ("document" if spec.scope == "document" else "page"),
        page_index=page_index,
        source=source,
        details=jsonable(details or {}),
        notes=notes,
        confidence=jsonable(confidence),
    )


class PageAnalysis(BaseModel):
    page_index: int
    width_pt: float
    height_pt: float
    extraction_mode: str
    parameters: list[ParameterResult] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

    def get(self, pid: str) -> Optional[ParameterResult]:
        for p in self.parameters:
            if p.parameter_id == pid:
                return p
        return None


class DocumentAnalysis(BaseModel):
    source_file: str
    source_sha256: str
    page_count: int
    method_version: str = METHOD_VERSION
    config_hash: str = ""
    reference_profile: Optional[str] = None
    pages: list[PageAnalysis] = Field(default_factory=list)
    document_parameters: list[ParameterResult] = Field(default_factory=list)
    evaluation: dict[str, Any] = Field(default_factory=dict)
    recommendations: list[dict[str, Any]] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

    def get_doc(self, pid: str) -> Optional[ParameterResult]:
        for p in self.document_parameters:
            if p.parameter_id == pid:
                return p
        return None

    def all_parameters(self) -> list[ParameterResult]:
        out = list(self.document_parameters)
        for pg in self.pages:
            out.extend(pg.parameters)
        return out
