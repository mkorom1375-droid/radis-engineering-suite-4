from django.test import SimpleTestCase
from django.urls import resolve, reverse

from .views import health_check


class HealthCheckTests(SimpleTestCase):
    def test_health_check_returns_service_status(self):
        response = self.client.get(reverse("health-check"))

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["success"])
        self.assertEqual(payload["status"], "ok")
        self.assertEqual(payload["service"], "RADIS ENGINEERING SUITE API")
        self.assertIn("timestamp", payload)

    def test_health_url_resolves_to_health_check_view(self):
        match = resolve("/api/health/")

        self.assertIs(match.func, health_check)


class FoundationRoutingTests(SimpleTestCase):
    def test_inventory_api_is_registered(self):
        match = resolve("/api/inventory/warehouses/")

        self.assertEqual(match.url_name, "warehouse-list")
