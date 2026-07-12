"""Run-level selection + validation for a bounded live/offline execution (DevSpec Section 39).

One config, one lane, one explicit model, an explicit fixture subset. Selection is
deterministic and fails closed on every ambiguous or unapproved choice. The first-live
approved-set restriction is applied here from the config, never hardcoded into the corpus.
"""

from __future__ import annotations

from .fixtures import Fixture

# Capabilities the openai-native probe does NOT implement (probe.manifest.json
# known_limitations). A fixture requiring one of these is ineligible for that lane.
_LANE_UNSUPPORTED: dict[str, set[str]] = {
    "openai": {"embeddings", "multimodal", "vision", "image", "image_generation", "audio"},
}


class SelectionError(RuntimeError):
    """Raised to reject an invalid or unapproved run selection."""


def parse_fixture_ids(raw: str) -> list[str]:
    """Split a comma-separated fixture list, preserving order. Reject empty and duplicates."""
    ids = [part.strip() for part in raw.split(",") if part.strip()]
    if not ids:
        raise SelectionError("no fixtures selected (empty --fixtures)")
    seen: set[str] = set()
    dups: list[str] = []
    for fid in ids:
        if fid in seen:
            dups.append(fid)
        seen.add(fid)
    if dups:
        raise SelectionError(f"duplicate fixture ids: {', '.join(sorted(set(dups)))}")
    return ids


def select_lane(lanes: list[dict], lane_id: str | None) -> dict:
    if not lane_id:
        raise SelectionError("no lane selected (--lane is required)")
    matches = [ln for ln in lanes if ln.get("lane_id") == lane_id]
    if not matches:
        known = ", ".join(sorted(ln.get("lane_id", "?") for ln in lanes)) or "(none)"
        raise SelectionError(f"unknown lane {lane_id!r}; known lanes: {known}")
    return matches[0]


def resolve_model(lane: dict, model: str | None) -> dict:
    """Return the lane with an explicit model bound. A live/offline run needs a real model."""
    if not model:
        raise SelectionError("no model selected (--model is required for execution)")
    resolved = dict(lane)
    resolved["model"] = model
    return resolved


def _ineligible_caps(fx: Fixture, lane: dict) -> set[str]:
    unsupported = _LANE_UNSUPPORTED.get(lane.get("provider", ""), set())
    caps = set(fx.data.get("requirements", {}).get("capabilities", []))
    return caps & unsupported


def select_fixtures(
    all_fixtures: list[Fixture],
    ids: list[str],
    *,
    lane: dict,
    approved_fixtures: list[str] | None = None,
) -> list[Fixture]:
    """Resolve requested fixture ids to Fixtures in the requested order, failing closed.

    Rejects unknown ids, ids ineligible for the selected lane, and — when a first-live
    approved set is supplied — any id outside that set.
    """
    by_id = {fx.id: fx for fx in all_fixtures}

    unknown = [fid for fid in ids if fid not in by_id]
    if unknown:
        raise SelectionError(f"unknown fixture ids: {', '.join(unknown)}")

    if approved_fixtures is not None:
        approved = set(approved_fixtures)
        outside = [fid for fid in ids if fid not in approved]
        if outside:
            raise SelectionError(
                f"fixtures not in the approved first-live set: {', '.join(outside)}"
            )

    selected = [by_id[fid] for fid in ids]  # preserve caller order (deterministic)

    for fx in selected:
        bad = _ineligible_caps(fx, lane)
        if bad:
            raise SelectionError(
                f"fixture {fx.id} requires {', '.join(sorted(bad))} which lane "
                f"{lane.get('lane_id')} does not support"
            )
    return selected
