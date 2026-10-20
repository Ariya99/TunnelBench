"""Unit tests for Phase 7 Target-Service Validation (Google AI Studio / Gemini)."""

import unittest
from unittest.mock import MagicMock, patch
import urllib.error

from tunnelbench.models import CheckStatus, ErrorCode
from tunnelbench.validation.target_check import TargetServiceValidator


class TestTargetCheck(unittest.TestCase):

    def test_gemini_api_unauthenticated_reachability_pass(self):
        """Unauthenticated HTTP 400 from Google proves end-to-end transport reachability."""
        validator = TargetServiceValidator()

        fake_body = b'{\n  "error": {\n    "code": 400,\n    "message": "API key not valid. Please pass a valid API key.",\n    "status": "INVALID_ARGUMENT"\n  }\n}'
        http_error = urllib.error.HTTPError(
            url="https://generativelanguage.googleapis.com",
            code=400,
            msg="Bad Request",
            hdrs=MagicMock(),
            fp=MagicMock(read=lambda: fake_body),
        )

        with patch("urllib.request.OpenerDirector.open", side_effect=http_error):
            probe = validator.check_gemini_api()
            self.assertEqual(probe.status, CheckStatus.PASS)
            self.assertEqual(probe.details["http_code"], 400)
            self.assertTrue(probe.details["verified_transport"])

    def test_gemini_api_geo_restriction_fail(self):
        validator = TargetServiceValidator()

        fake_body = b'{\n  "error": {\n    "code": 403,\n    "message": "User location is not supported for the API use.",\n    "status": "PERMISSION_DENIED"\n  }\n}'
        http_error = urllib.error.HTTPError(
            url="https://generativelanguage.googleapis.com",
            code=403,
            msg="Forbidden",
            hdrs=MagicMock(),
            fp=MagicMock(read=lambda: fake_body),
        )

        with patch("urllib.request.OpenerDirector.open", side_effect=http_error):
            probe = validator.check_gemini_api()
            self.assertEqual(probe.status, CheckStatus.FAIL)
            self.assertEqual(probe.error_code, ErrorCode.HTTP_GEO_RESTRICTED)

    def test_gemini_api_generic_403_not_misclassified_as_geo(self):
        """Generic 403 without location evidence must not be classified as geo-restricted."""
        validator = TargetServiceValidator()

        fake_body = b'{\n  "error": {\n    "code": 403,\n    "message": "Custom policy blocked.",\n    "status": "UNKNOWN"\n  }\n}'
        http_error = urllib.error.HTTPError(
            url="https://generativelanguage.googleapis.com",
            code=403,
            msg="Forbidden",
            hdrs=MagicMock(),
            fp=MagicMock(read=lambda: fake_body),
        )

        with patch("urllib.request.OpenerDirector.open", side_effect=http_error):
            probe = validator.check_gemini_api()
            self.assertEqual(probe.status, CheckStatus.FAIL)
            self.assertEqual(probe.error_code, ErrorCode.UNKNOWN_ERROR)
            self.assertNotEqual(probe.error_code, ErrorCode.HTTP_GEO_RESTRICTED)

    def test_gemini_api_permission_403(self):
        validator = TargetServiceValidator()

        fake_body = b'{\n  "error": {\n    "code": 403,\n    "message": "Caller lacks required permission.",\n    "status": "PERMISSION_DENIED"\n  }\n}'
        http_error = urllib.error.HTTPError(
            url="https://generativelanguage.googleapis.com",
            code=403,
            msg="Forbidden",
            hdrs=MagicMock(),
            fp=MagicMock(read=lambda: fake_body),
        )

        with patch("urllib.request.OpenerDirector.open", side_effect=http_error):
            probe = validator.check_gemini_api()
            self.assertEqual(probe.status, CheckStatus.FAIL)
            self.assertEqual(probe.error_code, ErrorCode.HTTP_AUTH_REQUIRED)

    def test_gemini_api_network_timeout(self):
        validator = TargetServiceValidator()

        with patch("urllib.request.OpenerDirector.open", side_effect=TimeoutError("Connection timed out")):
            probe = validator.check_gemini_api()
            self.assertEqual(probe.status, CheckStatus.FAIL)
            self.assertEqual(probe.error_code, ErrorCode.TARGET_NETWORK_TIMEOUT)


if __name__ == "__main__":
    unittest.main()
