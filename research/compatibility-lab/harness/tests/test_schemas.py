"""Schema validation for compatibility artifacts."""

from __future__ import annotations

import json
from pathlib import Path

import jsonschema

ROOT = Path(__file__).resolve().parents[2]


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_compatibility_matrix_schema() -> None:
    schema = _load(ROOT / "spec" / "compatibility-matrix.schema.json")
    data = _load(ROOT / "reports" / "compatibility-matrix.json")
    jsonschema.validate(data, schema)
    assert "G2 or G3" in data["disclaimer"]


def test_endpoint_profile_example_schema() -> None:
    schema = _load(ROOT / "spec" / "endpoint-profile.schema.json")
    data = _load(ROOT / "examples" / "endpoint-profile.example.json")
    jsonschema.validate(data, schema)
    assert "https://" not in json.dumps(data)


def test_capability_profiles_deterministic() -> None:
    for name in ("openai-compatible-custom.json", "anthropic-compatible-custom.json"):
        data = _load(ROOT / "reports" / "capabilities" / name)
        assert data["evidence_class"] == "custom_endpoint_compatibility"
        assert "G2 or G3" in data["disclaimer"]
        assert data["capabilities"]["text_generation"] in {
            "declared",
            "observed_offline",
            "observed_live",
            "unsupported",
            "inconclusive",
            "not_tested",
        }
