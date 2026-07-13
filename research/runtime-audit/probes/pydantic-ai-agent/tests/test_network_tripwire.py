"""Process-level network tripwire for offline (mock) probe runs.

Independent of credential absence: even with a key present, a mock run must not open an OUTBOUND
socket. The asyncio loopback self-pipe (127.0.0.1) that an async Agent needs is allowed; every
other host is blocked. The harness sets ALMS_PROBE_BLOCK_NETWORK=1 for offline runs.
"""

from __future__ import annotations

import socket

import probe.__main__ as pm
import pytest


def test_tripwire_blocks_outbound_allows_loopback(monkeypatch):
    monkeypatch.setattr(socket.socket, "connect", lambda self, *a, **k: None)
    monkeypatch.setattr(socket.socket, "connect_ex", lambda self, *a, **k: 0)

    pm._install_network_tripwire()

    s = socket.socket()
    try:
        with pytest.raises(RuntimeError, match="network blocked"):
            s.connect(("8.8.8.8", 9))
        with pytest.raises(RuntimeError, match="network blocked"):
            s.connect_ex(("93.184.216.34", 9))
        # Loopback is allowed so the async event loop can run.
        assert s.connect(("127.0.0.1", 9)) is None
        assert s.connect_ex(("127.0.0.1", 9)) == 0
    finally:
        s.close()


def test_is_loopback_classification():
    assert pm._is_loopback(("127.0.0.1", 9)) is True
    assert pm._is_loopback(("::1", 9)) is True
    assert pm._is_loopback(("localhost", 80)) is True
    assert pm._is_loopback(("8.8.8.8", 443)) is False
    assert pm._is_loopback(("api.openai.com", 443)) is False
