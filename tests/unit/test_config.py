"""Unit tests for Configuration and VPS Profile Management."""

import tempfile
import unittest
from pathlib import Path

from tunnelbench.config import ConfigError, ConfigManager
from tunnelbench.models import VPSProfile


class TestConfig(unittest.TestCase):

    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.config_dir = Path(self.td.name)
        self.mgr = ConfigManager(config_dir=self.config_dir)

    def tearDown(self):
        self.td.cleanup()

    def test_add_and_get_profile(self):
        prof = self.mgr.add_profile(
            name="hetzner-fsn",
            host="10.0.0.10",
            port=22,
            user="root",
            tags=["germany", "hetzner"],
        )
        self.assertEqual(prof.name, "hetzner-fsn")
        self.assertEqual(prof.host, "10.0.0.10")

        retrieved = self.mgr.get_profile("hetzner-fsn")
        self.assertEqual(retrieved.name, prof.name)
        self.assertEqual(retrieved.host, prof.host)
        self.assertEqual(retrieved.tags, ["germany", "hetzner"])

    def test_invalid_profile_inputs(self):
        with self.assertRaises(ConfigError):
            self.mgr.add_profile(name="invalid name", host="10.0.0.1")

        with self.assertRaises(ConfigError):
            self.mgr.add_profile(name="bad-port", host="10.0.0.1", port=70000)

        with self.assertRaises(ConfigError):
            self.mgr.add_profile(name="bad-host", host="not an ip or host!")

    def test_profile_list_and_remove(self):
        self.mgr.add_profile(name="p1", host="10.0.0.1")
        self.mgr.add_profile(name="p2", host="10.0.0.2")

        profiles = self.mgr.list_profiles()
        self.assertEqual(len(profiles), 2)

        self.mgr.remove_profile("p1")
        self.assertEqual(len(self.mgr.list_profiles()), 1)

        with self.assertRaises(ConfigError):
            self.mgr.get_profile("p1")

    def test_profile_file_permissions(self):
        self.mgr.add_profile(name="secure-prof", host="10.0.0.1")
        stat_mode = self.mgr.profiles_file.stat().st_mode & 0o777
        self.assertEqual(stat_mode, 0o600)


if __name__ == "__main__":
    unittest.main()
