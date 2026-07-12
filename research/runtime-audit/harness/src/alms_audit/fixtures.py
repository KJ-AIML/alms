"""Discover and load fixture definitions from `<root>/fixtures/**/*.json`."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .schemas import default_root


@dataclass(frozen=True)
class Fixture:
    path: Path
    data: dict

    @property
    def id(self) -> str:
        return self.data.get("id", "<missing-id>")

    @property
    def feature(self) -> str:
        return self.data.get("feature", "<missing-feature>")

    @property
    def summary(self) -> str:
        return self.data.get("summary", "")

    @property
    def tier(self) -> str:
        return self.data.get("tier", "")

    @property
    def cost_class(self) -> str:
        return self.data.get("cost_class", "")

    @property
    def live_required(self) -> bool:
        return bool(self.data.get("requirements", {}).get("live_required"))


def fixtures_dir(root: Path | None = None) -> Path:
    return (root or default_root()) / "fixtures"


def load_fixtures(root: Path | None = None) -> list[Fixture]:
    base = fixtures_dir(root)
    if not base.is_dir():
        return []
    out: list[Fixture] = []
    for path in sorted(base.rglob("*.json")):
        out.append(Fixture(path=path, data=json.loads(path.read_text(encoding="utf-8"))))
    # Deterministic, id-sorted order for listing and validation.
    return sorted(out, key=lambda f: f.id)


def duplicate_ids(fixtures: list[Fixture]) -> list[str]:
    """Return fixture IDs that appear more than once (sorted, unique)."""
    seen: dict[str, int] = {}
    for f in fixtures:
        seen[f.id] = seen.get(f.id, 0) + 1
    return sorted(fid for fid, n in seen.items() if n > 1)
