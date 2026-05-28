from django.test import TestCase
from django.urls import reverse


class SwaggerTestCase(TestCase):
    def test_swagger_schema_generation(self):
        """Verify that the Swagger OpenAPI schema generates successfully without errors."""
        url = reverse("kependudukan:schema-swagger-ui") + "?format=openapi"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
