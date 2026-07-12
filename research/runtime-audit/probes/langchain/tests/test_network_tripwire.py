"""Process-level network tripwire for offline (mock) probe runs.

Independent of credential absence: even with a key present, a mock run must not open a
socket. The harness sets ALMS_PROBE_BLOCK_NETWORK=1 for offline runs.
"""

from __future__ import annotations

import socket

import probe.__main__ as pm
import pytest


def test_install_network_tripwire_blocks_connect(monkeypatch):
    monkeypatch.setattr(socket.socket, "connect", lambda self, *a, **k: None)
    monkeypatch.setattr(socket.socket, "connect_ex", lambda self, *a, **k: 0)

    pm._install_network_tripwire()

    s = socket.socket()
    try:
        with pytest.raises(RuntimeError, match="network blocked"):
            s.connect(("127.0.0.1", 9))
        with pytest.raises(RuntimeError, match="network blocked"):
            s.connect_ex(("127.0.0.1", 9))
    finally:
        s.close()
