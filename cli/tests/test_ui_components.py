"""Tests for CLI UI components — encoding safety."""

import io
import sys
from unittest.mock import patch

import alms_cli.ui.components as comp


def test_symbols_ascii_safe_when_unicode_unsupported():
    """When stdout can't encode Unicode, symbols must be ASCII-safe."""
    fake_stdout = io.TextIOWrapper(io.BytesIO(), encoding="cp1252")
    with patch.object(sys, "stdout", fake_stdout):
        assert not comp._stdout_supports_unicode()


def test_print_functions_no_crash_on_cp1252():
    """print_* functions must not crash on cp1252-encoded stdout."""
    fake_stdout = io.TextIOWrapper(io.BytesIO(), encoding="cp1252")
    with patch.object(sys, "stdout", fake_stdout):
        import importlib

        importlib.reload(comp)
        # These must not raise UnicodeEncodeError
        comp.print_success("ok")
        comp.print_error("fail")
        comp.print_info("note")
        comp.print_warning("warn")
