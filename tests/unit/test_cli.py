"""Unit tests for Command Line Interface dispatch and parsing."""

import io
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from tunnelbench.cli import build_parser, main


class TestCLI(unittest.TestCase):

    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.temp_dir = Path(self.td.name)

    def tearDown(self):
        self.td.cleanup()

    def test_cli_help(self):
        parser = build_parser()
        help_text = parser.format_help()
        self.assertIn("tunnelbench", help_text)
        self.assertIn("doctor", help_text)

    def test_cli_doctor(self):
        with patch.dict(os.environ, {"TUNNELBENCH_REPORT_DIR": str(self.temp_dir / "reports")}):
            buf = io.StringIO()
            with redirect_stdout(buf):
                exit_code = main(["doctor"])
            self.assertEqual(exit_code, 0)
            self.assertIn("TunnelBench Preflight Doctor", buf.getvalue())

    def test_cli_candidates_list(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            exit_code = main(["candidates", "list"])
        self.assertEqual(exit_code, 0)
        output = buf.getvalue()
        self.assertIn("xray-reality", output)
        self.assertIn("SUPPORTED", output)

    def test_cli_vps_lifecycle(self):
        with patch.dict(os.environ, {"TUNNELBENCH_CONFIG_DIR": str(self.temp_dir / "config")}):
            # 1. Add
            buf = io.StringIO()
            with redirect_stdout(buf):
                rc_add = main(["vps", "add", "--name", "cli-test", "--host", "198.51.100.10"])
            self.assertEqual(rc_add, 0)

            # 2. List
            buf = io.StringIO()
            with redirect_stdout(buf):
                rc_list = main(["vps", "list"])
            self.assertEqual(rc_list, 0)
            self.assertIn("cli-test", buf.getvalue())

            # 3. Show
            buf = io.StringIO()
            with redirect_stdout(buf):
                rc_show = main(["vps", "show", "cli-test"])
            self.assertEqual(rc_show, 0)
            self.assertIn("198.51.100.10", buf.getvalue())

            # 4. Remove
            buf = io.StringIO()
            with redirect_stdout(buf):
                rc_rm = main(["vps", "remove", "cli-test"])
            self.assertEqual(rc_rm, 0)


if __name__ == "__main__":
    unittest.main()
