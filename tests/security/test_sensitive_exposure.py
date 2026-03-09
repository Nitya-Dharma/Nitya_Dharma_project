# Phase 9.6: Sensitive information exposure tests
from django.test import TestCase, Client, override_settings


class TestSensitiveExposure(TestCase):
    """With DEBUG=False, error responses must not leak stack traces, SQL, or paths."""

    def setUp(self):
        self.client = Client()

    @override_settings(DEBUG=False)
    def test_404_response_no_sensitive_leak(self):
        response = self.client.get("/nonexistent-url-404-test/")
        self.assertIn(response.status_code, (404, 500))
        content = response.content.decode("utf-8", errors="replace")
        self.assertNotIn("Traceback", content)
        self.assertNotIn("File \"", content)
        self.assertNotIn(".py\", line", content)

    @override_settings(DEBUG=False)
    def test_error_response_no_sql_or_paths(self):
        response = self.client.get("/nonexistent-url-404-test/")
        content = response.content.decode("utf-8", errors="replace").lower()
        self.assertNotIn("select ", content)
        self.assertNotIn("insert into", content)
        self.assertNotIn("c:\\", content)
        self.assertNotIn("/etc/", content)
        self.assertNotIn("secret_key", content)
        self.assertNotIn("database_password", content)
