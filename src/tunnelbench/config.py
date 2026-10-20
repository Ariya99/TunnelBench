"""Configuration and VPS Profile Management for TunnelBench.

Strictly adheres to zero-secret persistence. Profiles contain only non-secret
connection coordinates (host, port, user, key_path, tags).
"""

from __future__ import annotations

import ipaddress
import json
import os
import re
from pathlib import Path
from typing import Dict, List, Optional

from tunnelbench.models import VPSProfile


_HOSTNAME_REGEX = re.compile(
    r"^(([a-zA-Z0-9]|[a-zA-Z0-9][a-zA-Z0-9\-]*[a-zA-Z0-9])\.)*([A-Za-z0-9]|[A-Za-z0-9][A-Za-z0-9\-]*[A-Za-z0-9])$"
)
_PROFILE_NAME_REGEX = re.compile(r"^[a-zA-Z0-9_\-]+$")
_USERNAME_REGEX = re.compile(r"^[a-zA-Z0-9_.][a-zA-Z0-9_.-]*$")


class ConfigError(Exception):
    """Raised for invalid configurations or profile validation failures."""
    pass


class ConfigManager:
    """Manages persistent VPS profiles and tool configuration."""

    def __init__(self, config_dir: Optional[Path] = None) -> None:
        if config_dir is None:
            env_dir = os.environ.get("TUNNELBENCH_CONFIG_DIR")
            if env_dir:
                self.config_dir = Path(env_dir)
            else:
                preferred = Path(os.path.expanduser("~/.config/tunnelbench"))
                try:
                    preferred.mkdir(parents=True, exist_ok=True, mode=0o700)
                    self.config_dir = preferred
                except OSError:
                    self.config_dir = Path.cwd() / ".tunnelbench" / "config"
        else:
            self.config_dir = Path(config_dir)

        self.profiles_file = self.config_dir / "profiles.json"
        self._ensure_config_dir()

    def _ensure_config_dir(self) -> None:
        """Creates config directory with safe permissions if not existing."""
        if not self.config_dir.exists():
            self.config_dir.mkdir(parents=True, exist_ok=True, mode=0o700)

    @staticmethod
    def validate_profile_inputs(
        name: str,
        host: str,
        port: int,
        user: str,
        auth_method: str = "key",
        key_path: Optional[str] = None,
    ) -> None:
        """Validates all profile attributes before saving."""
        if not name or not _PROFILE_NAME_REGEX.match(name):
            raise ConfigError(
                f"Invalid profile name '{name}'. Must contain only alphanumeric characters, underscores, and dashes."
            )

        if not (1 <= port <= 65535):
            raise ConfigError(f"Invalid port {port}. Must be between 1 and 65535.")

        if not user or not _USERNAME_REGEX.match(user):
            raise ConfigError(f"Invalid username '{user}'.")

        # Validate host (either IP address or valid hostname)
        is_ip = False
        try:
            ipaddress.ip_address(host)
            is_ip = True
        except ValueError:
            pass

        if not is_ip:
            if len(host) > 253 or not _HOSTNAME_REGEX.match(host):
                raise ConfigError(
                    f"Invalid host '{host}'. Must be a valid IPv4/IPv6 address or RFC-compliant hostname."
                )

        if auth_method not in ("key", "agent"):
            raise ConfigError(f"Unsupported auth_method '{auth_method}'. Use 'key' or 'agent'.")

        if auth_method == "key" and key_path:
            p = Path(os.path.expanduser(key_path))
            if not p.exists():
                raise ConfigError(f"Specified SSH key file does not exist: {key_path}")

    def load_profiles(self) -> Dict[str, VPSProfile]:
        """Loads all stored VPS profiles from disk."""
        if not self.profiles_file.exists():
            return {}
        try:
            with open(self.profiles_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            return {name: VPSProfile.from_dict(prof) for name, prof in data.items()}
        except Exception as e:
            raise ConfigError(f"Failed to load profiles from {self.profiles_file}: {e}") from e

    def save_profiles(self, profiles: Dict[str, VPSProfile]) -> None:
        """Persists profiles to disk with strict permissions (0o600)."""
        self._ensure_config_dir()
        data = {name: prof.to_dict() for name, prof in profiles.items()}
        temp_file = self.profiles_file.with_suffix(".tmp")
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        temp_file.chmod(0o600)
        temp_file.replace(self.profiles_file)

    def add_profile(
        self,
        name: str,
        host: str,
        port: int = 22,
        user: str = "root",
        auth_method: str = "key",
        key_path: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> VPSProfile:
        """Validates and stores a new VPS profile."""
        self.validate_profile_inputs(
            name=name,
            host=host,
            port=port,
            user=user,
            auth_method=auth_method,
            key_path=key_path,
        )
        profiles = self.load_profiles()
        profile = VPSProfile(
            name=name,
            host=host,
            port=port,
            user=user,
            auth_method=auth_method,
            key_path=key_path,
            tags=tags or [],
        )
        profiles[name] = profile
        self.save_profiles(profiles)
        return profile

    def get_profile(self, name: str) -> VPSProfile:
        """Retrieves a named profile or raises ConfigError."""
        profiles = self.load_profiles()
        if name not in profiles:
            raise ConfigError(f"Profile '{name}' not found. Available: {list(profiles.keys())}")
        return profiles[name]

    def remove_profile(self, name: str) -> None:
        """Deletes a named profile."""
        profiles = self.load_profiles()
        if name not in profiles:
            raise ConfigError(f"Profile '{name}' not found.")
        del profiles[name]
        self.save_profiles(profiles)

    def list_profiles(self) -> List[VPSProfile]:
        """Returns list of all registered profiles."""
        return list(self.load_profiles().values())
