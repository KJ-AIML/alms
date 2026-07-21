"""P0.7C: consolidated finding ledger and phase 0 gate matrix validation."""

from __future__ import annotations

import json

from alms_audit.schemas import default_root, validation_errors


def _load_json(name: str) -> dict:
    root = default_root()
    return json.loads((root / "reports" / name).read_text(encoding="utf-8"))


def test_finding_ledger_validates():
    root = default_root()
    ledger = _load_json("finding-ledger.json")
    assert ledger["generated_offline"] is True
    assert validation_errors("finding-ledger", ledger, root) == []
    ids = {f["id"] for f in ledger["findings"]}
    assert ids >= {"N-01", "N-02", "N-03", "N-04", "N-05", "L-01"}
    for finding in ledger["findings"]:
        assert validation_errors("finding", finding, root) == [], finding["id"]
    l01 = next(f for f in ledger["findings"] if f["id"] == "L-01")
    assert l01["status"] == "proposed"
    assert len(ledger["observations"]) >= 1
    assert any(o["lane"] == "pydantic-ai-agent" for o in ledger["observations"])


def test_phase0_gate_matrix_validates():
    root = default_root()
    matrix = _load_json("phase0-gate-matrix.json")
    assert matrix["generated_offline"] is True
    assert validation_errors("phase0-gate-matrix", matrix, root) == []
    by_id = {g["id"]: g for g in matrix["gates"]}
    assert set(by_id) >= {"G0", "G1", "G2", "G3", "G4", "G5", "G6", "G7"}
    assert by_id["G2"]["status"] == "blocked_credential"
    assert by_id["G3"]["status"] == "blocked_credential"
    assert by_id["G7"]["status"] == "not_started"
    assert by_id["G7"]["status"] != "blocked_credential"
    g2_action = by_id["G2"]["action_required"] or ""
    assert "langchain-openai" not in g2_action
    assert "langchain" in g2_action
    exit12 = by_id["EXIT-12"]
    assert exit12["status"] == "deferred"
    assert "P0.9_Q005_EMBEDDING_DEFERRAL" in (exit12["evidence"] or "")
    # Phase 0 must not be claimed complete while live gates remain.
    live_blocked = [
        g
        for g in matrix["gates"]
        if g["status"] in ("blocked_credential", "pending_live", "not_started")
        and g["id"].startswith(("G", "EXIT"))
    ]
    assert len(live_blocked) >= 5
