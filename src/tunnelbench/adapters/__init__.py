"""Protocol adapter subsystem for TunnelBench."""

from tunnelbench.adapters.base import BaseAdapter, get_adapter, list_adapters
from tunnelbench.adapters.ssh_socks import SSHSocksAdapter
from tunnelbench.adapters.xray_reality import XrayRealityAdapter

__all__ = [
    "BaseAdapter",
    "get_adapter",
    "list_adapters",
    "XrayRealityAdapter",
    "SSHSocksAdapter",
]
