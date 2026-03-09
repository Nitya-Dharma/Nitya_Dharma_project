# Phase 9.5/9.5A: SQL injection detection tests (TestCase = automatic rollback; no permanent DB changes)
from django.test import TestCase, Client
from django.urls import reverse


class TestSqlInjection(TestCase):
    """Test that search and API endpoints reject or safely handle SQL injection payloads."""

    def setUp(self):
        self.client = Client()

    def test_search_pandits_injection_payload_or(self):
        # Realistic query-manipulation payloads (no multi-statement); expect safe response
        payloads = [
            "' OR 1=1 --",
            "admin' OR '1'='1",
            "1 OR 1=1",
            "' OR ''='",
        ]
        for payload in payloads:
            response = self.client.get(
                reverse("search_api:search_pandits"),
                {"city_id": payload, "page": 1},
            )
            self.assertIn(
                response.status_code, (200, 400),
                f"Expected 200 or 400 for city_id={payload!r}",
            )
            self.assertNotIn(b"ProgrammingError", response.content)
            self.assertNotIn(b"OperationalError", response.content)
            self.assertNotIn(b"sqlite3", response.content, "Must not expose DB engine")
            self.assertNotIn(b"mysql", response.content, "Must not expose DB engine")

    def test_search_pandits_injection_union(self):
        response = self.client.get(
            reverse("search_api:search_pandits"),
            {"city_id": "1 UNION SELECT password FROM accounts_user"},
        )
        self.assertIn(response.status_code, (200, 400))
        self.assertNotIn(b"ProgrammingError", response.content)
        self.assertNotIn(b"OperationalError", response.content)
