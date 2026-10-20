"""Unit tests for Centralized Secret Redaction Engine."""

import unittest
from tunnelbench.redaction import RedactionEngine, redact


class TestRedaction(unittest.TestCase):

    def test_redact_uuid(self):
        raw = "Client connection with UUID 12345678-1234-4234-8234-123456789abc initialized."
        redacted = redact(raw)
        self.assertNotIn("12345678-1234-4234-8234-123456789abc", redacted)
        self.assertIn("[REDACTED_UUID]", redacted)

    def test_redact_pem_private_key(self):
        pem = """-----BEGIN RSA PRIVATE KEY-----
MIIEowIBAAKCAQEA0Y1+exampleFakeKeyPayloadForTestingOnlyDoNotUse==
-----END RSA PRIVATE KEY-----"""
        text = f"Server loaded key:\n{pem}\nKey check completed."
        redacted = redact(text)
        self.assertNotIn("MIIEowIB", redacted)
        self.assertIn("[REDACTED_PRIVATE_KEY]", redacted)

    def test_redact_google_api_key(self):
        text = "Query failed: invalid key AIzaSyD1234567890abcdefghijklmnopqrstuv"
        redacted = redact(text)
        self.assertNotIn("AIzaSy", redacted)
        self.assertIn("[REDACTED_API_KEY]", redacted)

    def test_redact_bearer_token(self):
        text = "Authorization: Bearer ya29.a0AWY7Ckm_fakeTokenString123456789"
        redacted = redact(text)
        self.assertNotIn("ya29.", redacted)
        self.assertIn("Bearer [REDACTED_TOKEN]", redacted)

    def test_redact_connection_uris(self):
        uris = [
            "vless://9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d@198.51.100.1:443?security=reality#Node",
            "vmess://eyJhZGQiOiIxOTguNTEuMTAwLjEiLCJwb3J0IjoiNDQzIn0=",
            "ss://YWVzLTI1Ni1nY206cGFzc3dvcmRAMTk4LjUxLjEwMC4xOjgzODg=#Node",
            "trojan://password123@198.51.100.1:443#Node",
        ]
        for u in uris:
            res = redact(f"Connection URL: {u}")
            self.assertNotIn("9b1deb4d", res)
            self.assertNotIn("eyJhZGQi", res)
            self.assertNotIn("YWVzLTI1", res)
            self.assertNotIn("password123", res)
            self.assertIn("[REDACTED_URI]", res)

    def test_recursive_structure_redaction(self):
        data = {
            "user": "alice",
            "api_key": "AIzaSyA1234567890123456789012345678901",
            "nested": {
                "uuid": "e8a93a1c-30b1-4f11-92df-42fa883cb099",
                "list_of_uris": [
                    "vless://secret@example.com:443",
                    "normal_string",
                ],
            },
            "count": 42,
        }
        redacted = redact(data)
        self.assertEqual(redacted["api_key"], "[REDACTED_API_KEY]")
        self.assertEqual(redacted["nested"]["uuid"], "[REDACTED_UUID]")
        self.assertEqual(redacted["nested"]["list_of_uris"][0], "vless://[REDACTED_URI]")
        self.assertEqual(redacted["nested"]["list_of_uris"][1], "normal_string")
        self.assertEqual(redacted["count"], 42)


if __name__ == "__main__":
    unittest.main()
