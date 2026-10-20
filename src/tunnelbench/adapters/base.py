"""Base Protocol Adapter Contract and Registry.

Enforces prerequisite checks, explicit deployment plans, user approval gates,
and clean lifecycle management across all VPN/tunnel implementations.
"""

from __future__ import annotations

import abc
from typing import Any, Dict, List, Optional, Tuple

from tunnelbench.models import AdapterStatus, CheckStatus, DeploymentPlan, ProbeResult, VPSProfile
from tunnelbench.remote.ssh import SSHClient


class BaseAdapter(abc.ABC):
    """Abstract base class for all tunnel and proxy adapters."""

    name: str = ""
    display_name: str = ""
    status: AdapterStatus = AdapterStatus.EXPERIMENTAL
    description: str = ""

    @abc.abstractmethod
    def check_prerequisites(self, profile: VPSProfile, ssh: SSHClient) -> List[ProbeResult]:
        """Validates VPS suitability and required tools before deployment."""
        pass

    @abc.abstractmethod
    def build_deployment_plan(
        self, profile: VPSProfile, options: Optional[Dict[str, Any]] = None
    ) -> DeploymentPlan:
        """Constructs a deterministic, human-readable plan describing all proposed modifications."""
        pass

    def require_user_approval(
        self, plan: DeploymentPlan, auto_approve: bool = False
    ) -> bool:
        """Approval gate preventing unconfirmed server modification.

        If auto_approve is True (via explicit CLI --yes), proceeds automatically.
        Otherwise prompts the operator for explicit confirmation.
        """
        if auto_approve:
            return True

        print("\n" + "=" * 65)
        print(f" PROPOSED DEPLOYMENT PLAN: {plan.adapter_name}")
        print("=" * 65)
        print(f"Target VPS:        {plan.target_vps}")
        if plan.container_image:
            print(f"Container Image:   {plan.container_image}")
        if plan.config_path:
            print(f"Config File:       {plan.config_path}")
        print(f"Exposed Ports:     {plan.exposed_ports}")
        print("\nProposed Actions:")
        for idx, action in enumerate(plan.actions, 1):
            print(f"  {idx}. {action}")
        print("=" * 65)

        try:
            choice = input("\nDo you approve executing these actions on the remote VPS? [y/N]: ")
            return choice.strip().lower() in ("y", "yes")
        except (KeyboardInterrupt, EOFError):
            return False

    @abc.abstractmethod
    def deploy(
        self, profile: VPSProfile, plan: DeploymentPlan, ssh: SSHClient
    ) -> Tuple[bool, List[ProbeResult], Dict[str, Any]]:
        """Executes the approved deployment plan on the VPS."""
        pass

    @abc.abstractmethod
    def health_check(self, profile: VPSProfile, ssh: SSHClient) -> List[ProbeResult]:
        """Validates that the deployed service is active, listening, and error-free."""
        pass

    @abc.abstractmethod
    def cleanup(self, profile: VPSProfile, ssh: SSHClient) -> Tuple[bool, List[ProbeResult]]:
        """Removes deployed containers, processes, and configurations cleanly."""
        pass


# Global Adapter Registry
_REGISTRY: Dict[str, BaseAdapter] = {}


def register_adapter(adapter: BaseAdapter) -> None:
    """Registers an adapter instance."""
    _REGISTRY[adapter.name] = adapter


def get_adapter(name: str) -> BaseAdapter:
    """Retrieves an adapter by name or raises KeyError."""
    if name not in _REGISTRY:
        raise KeyError(
            f"Adapter '{name}' not found. Available adapters: {list(_REGISTRY.keys())}"
        )
    return _REGISTRY[name]


def list_adapters() -> List[BaseAdapter]:
    """Returns all registered adapters."""
    return list(_REGISTRY.values())
