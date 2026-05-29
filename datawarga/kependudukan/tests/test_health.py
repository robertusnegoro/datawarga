from unittest.mock import patch
from django.db.utils import OperationalError
from django.test import TestCase
from django.urls import reverse


class HealthCheckTestCase(TestCase):
    def test_health_liveness_check(self):
        """Test that /health and /api/health return 200 and indicate status is UP."""
        for url_name in ["kependudukan:health_check", "kependudukan:api_health_check"]:
            with self.subTest(url_name=url_name):
                url = reverse(url_name)
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200)

                data = response.json()
                self.assertEqual(data["status"], "UP")
                self.assertIn("timestamp", data)

    def test_ready_check_healthy(self):
        """Test that /ready and /api/ready return 200 and UP status when database is healthy."""
        for url_name in ["kependudukan:ready_check", "kependudukan:api_ready_check"]:
            with self.subTest(url_name=url_name):
                url = reverse(url_name)
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200)

                data = response.json()
                self.assertEqual(data["status"], "UP")
                self.assertEqual(data["components"]["database"]["status"], "UP")
                self.assertIn("timestamp", data)

    @patch("kependudukan.views.health.connections")
    def test_ready_check_unhealthy(self, mock_connections):
        """Test that /ready and /api/ready return 503 and DOWN status when database connection fails."""
        # Set up mock database connection cursor to raise an OperationalError when executing query
        mock_conn = mock_connections.__getitem__.return_value
        mock_cursor = mock_conn.cursor.return_value.__enter__.return_value
        mock_cursor.execute.side_effect = OperationalError("Connection refused")

        for url_name in ["kependudukan:ready_check", "kependudukan:api_ready_check"]:
            with self.subTest(url_name=url_name):
                url = reverse(url_name)
                response = self.client.get(url)
                self.assertEqual(response.status_code, 503)

                data = response.json()
                self.assertEqual(data["status"], "DOWN")
                self.assertEqual(data["components"]["database"]["status"], "DOWN")
                self.assertIn(
                    "Connection refused", data["components"]["database"]["message"]
                )
