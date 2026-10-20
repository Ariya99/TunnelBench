"""Pytest fixtures and test helpers for TunnelBench."""

from __future__ import annotations

import tempfile
from pathlib import Path

try:
    import pytest

    @pytest.fixture
    def temp_dir():
        with tempfile.TemporaryDirectory() as td:
            yield Path(td)

    @pytest.fixture
    def sample_vps_profile():
        from tunnelbench.models import VPSProfile
        return VPSProfile(
            name="test-vps",
            host="198.51.100.1",
            port=22,
            user="root",
            auth_method="key",
            tags=["unit-test", "eu"],
        )

except ImportError:
    pass
