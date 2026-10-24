"""Configuration loading: defaults + optional user YAML (deep merge)."""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Optional

import yaml

_DEFAULT = Path(__file__).with_name("default_config.yaml")


def _merge(a: dict, b: dict) -> dict:
    out = copy.deepcopy(a)
    for k, v in (b or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _merge(out[k], v)
        else:
            out[k] = copy.deepcopy(v)
    return out


def load_config(path: Optional[str] = None, overrides: Optional[dict] = None) -> dict:
    with open(_DEFAULT, encoding="utf-8") as fh:
        cfg = yaml.safe_load(fh)
    if path:
        with open(path, encoding="utf-8") as fh:
            cfg = _merge(cfg, yaml.safe_load(fh) or {})
    if overrides:
        cfg = _merge(cfg, overrides)
    return cfg


def config_hash(cfg: dict) -> str:
    return hashlib.sha256(json.dumps(cfg, sort_keys=True, default=str).encode()).hexdigest()[:16]
