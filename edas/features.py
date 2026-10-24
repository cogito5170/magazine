"""Comparable scalar feature vector (used for reference profiles, similarity,
re-ranking and rhythm).

Each key is ``PARAM`` or ``PARAM.path.to.leaf`` into a ParameterResult value.
Keys are grouped by module so that per-module distances can be computed.
Only scalars defined identically for every document go here (per-font or
per-image dictionaries are summarised by their page-level entries).
"""
from __future__ import annotations

from typing import Optional

from .schema import ParameterResult

FEATURES: dict[str, list[str]] = {
    "layout": ["A01", "A02.n", "A03.horizontal", "A03.vertical", "A04.M_l", "A04.M_r", "A04.M_t", "A04.M_b",
               "A05.horizontal", "A05.vertical", "A06", "A07", "A08", "A09", "A12", "A13.var_x", "A13.var_y",
               "A14", "A15", "A16.mean_nn", "A16.clark_evans_R", "A19.object_count", "A19.edge_density",
               "A19.region_count"],
    "typography": ["B03", "B04.page_mean", "B05.page_mean", "B06.page_mean", "B07.page_mean", "B10.median",
                   "B11", "B12.median", "B14", "B15", "B18.median"],
    "photography": ["C02.area_weighted_mean", "C03.area_weighted_mean", "C05.area_weighted_mean",
                    "C06.area_weighted_mean", "C08.area_weighted_mean", "C10.area_weighted_mean",
                    "C11.area_weighted_mean", "C13.area_weighted_mean", "C16.area_weighted_mean.left_right"],
    "composition": ["D01.0", "D01.1", "D02", "D03", "D04", "D06", "D07", "D09", "D11.luminance", "D11.log_area",
                    "D13.components", "D13.mean_clustering_coefficient", "D14", "D15", "D16"],
}
ALL_KEYS = [k for ks in FEATURES.values() for k in ks]
MODULE_OF = {k: m for m, ks in FEATURES.items() for k in ks}
# keys whose definition differs between PDF-object and raster extraction
SOURCE_DEPENDENT = {"B03", "B04.page_mean", "B05.page_mean", "B06.page_mean", "B07.page_mean",
                    "B10.median", "B11", "B12.median"}


def _leaf(v, path: list[str]):
    for p in path:
        if isinstance(v, dict):
            v = v.get(p)
        elif isinstance(v, list) and p.isdigit() and int(p) < len(v):
            v = v[int(p)]
        else:
            return None
    if isinstance(v, bool):
        return float(v)
    return float(v) if isinstance(v, (int, float)) else None


def page_values(params: list[ParameterResult]) -> dict[str, object]:
    return {p.parameter_id: p.value for p in params}


def extract(values: dict[str, object], keys: Optional[list[str]] = None) -> dict[str, Optional[float]]:
    out = {}
    for k in keys or ALL_KEYS:
        pid, *path = k.split(".")
        out[k] = _leaf(values.get(pid), path)
    return out
