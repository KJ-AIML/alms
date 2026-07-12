"""Load runtime lane definitions from `<root>/configs/lanes.json`.

A lane records three independent identifiers — runtime_layer, provider, model —
never collapsed into one string (DevSpec Section 29). Model ids are supplied at execution
time, so the committed lane config leaves `model` as null/placeholder (DevSpec Section 15).
"""

from __future__ import annotations

import json
from pathlib import Path

from .schemas import default_root


def lanes_path(root: Path | None = None) -> Path:
    return (root or default_root()) / "configs" / "lanes.json"


def load_lanes(root: Path | None = None) -> list[dict]:
    path = lanes_path(root)
    if not path.is_file():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    return data.get("lanes", [])
