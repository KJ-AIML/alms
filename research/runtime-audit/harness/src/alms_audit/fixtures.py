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


def fixtures_dir(root: Path | None = None) -> Path:
    return (root or default_root()) / "fixtures"


def load_fixtures(root: Path | None = None) -> list[Fixture]:
    base = fixtures_dir(root)
    if not base.is_dir():
        return []
    out: list[Fixture] = []
    for path in sorted(base.rglob("*.json")):
        out.append(Fixture(path=path, data=json.loads(path.read_text(encoding="utf-8"))))
    return out
