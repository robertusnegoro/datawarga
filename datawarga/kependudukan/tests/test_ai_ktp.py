import io
from unittest.mock import patch, MagicMock
from django.test import TestCase, override_settings
from django.urls import reverse
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image

from ..ai.ai_utils import optimize_image, parse_extracted_json, map_extracted_data
from ..ai.ai_service import OllamaProvider, OpenRouterProvider, get_ai_provider
from ..models import Warga, Kompleks


class AIUtilsTestCase(TestCase):
    def test_optimize_image(self):
        # Create a dummy RGBA image in memory
        im = Image.new("RGBA", (1000, 1000), (255, 0, 0, 255))
        im_io = io.BytesIO()
        im.save(im_io, "PNG")
        raw_bytes = im_io.getvalue()

        # Optimize image
        optimized = optimize_image(raw_bytes, max_size=(500, 500), quality=75)

        # Verify the optimized image is JPEG and resized
        opt_im = Image.open(io.BytesIO(optimized))
        self.assertEqual(opt_im.format, "JPEG")
        self.assertLessEqual(opt_im.size[0], 500)
        self.assertLessEqual(opt_im.size[1], 500)
        self.assertLess(len(optimized), len(raw_bytes))

    def test_parse_extracted_json_raw(self):
        json_str = '{"nik": "1234567890123456", "nama": "BUDI SANTOSO", "alamat_ktp": "Jl. Merdeka No. 1", "jenis_kelamin": "Laki-laki", "agama": "Islam"}'
        result = parse_extracted_json(json_str)
        self.assertEqual(result["nik"], "1234567890123456")
        self.assertEqual(result["nama"], "BUDI SANTOSO")

    def test_parse_extracted_json_markdown_block(self):
        markdown_str = (
            '```json\n{"nik": "1234567890123456", "nama": "BUDI SANTOSO"}\n```'
        )
        result = parse_extracted_json(markdown_str)
        self.assertEqual(result["nik"], "1234567890123456")
        self.assertEqual(result["nama"], "BUDI SANTOSO")

    def test_parse_extracted_json_raw_codeblock(self):
        markdown_str = '```\n{"nik": "1234567890123456"}\n```'
        result = parse_extracted_json(markdown_str)
        self.assertEqual(result["nik"], "1234567890123456")

    def test_parse_extracted_json_fallback(self):
        messy_str = 'Here is the JSON object: {"nik": "1234567890123456"} and some trailing words.'
        result = parse_extracted_json(messy_str)
        self.assertEqual(result["nik"], "1234567890123456")

    def test_parse_extracted_json_invalid(self):
        with self.assertRaises(ValueError):
            parse_extracted_json("invalid json content")

    def test_map_extracted_data_basic(self):
        raw_data = {
            "nik": "1234.5678.9012.3456",
            "nama": "  BUDI SANTOSO ",
            "alamat_ktp": "Jl. Merdeka No. 1",
            "jenis_kelamin": "LAKI - LAKI (MALE)",
            "agama": "ISLAM  ",
            "tempat_lahir": "  Jakarta ",
            "tanggal_lahir": "31-12-2026",
        }
        mapped = map_extracted_data(raw_data)
        self.assertEqual(mapped["nik"], "1234567890123456")
        self.assertEqual(mapped["nama_lengkap"], "BUDI SANTOSO")
        self.assertEqual(mapped["alamat_ktp"], "Jl. Merdeka No. 1")
        self.assertEqual(mapped["jenis_kelamin"], "LAKI-LAKI")
        self.assertEqual(mapped["agama"], "ISLAM")
        self.assertEqual(mapped["tempat_lahir"], "JAKARTA")
        self.assertEqual(mapped["tanggal_lahir"], "2026-12-31")

    def test_map_extracted_data_religion_gender_fallbacks(self):
        raw_data = {
            "nik": "12345",
            "nama_lengkap": "SITI AMINAH",
            "alamat": "Jl. Kenanga",
            "gender": "perempuan / female",
            "religion": "kristen protestan",
            "tempat": "BANDUNG",
            "tanggal": "1990/05/17",
        }
        mapped = map_extracted_data(raw_data)
        self.assertEqual(mapped["nik"], "12345")
        self.assertEqual(mapped["nama_lengkap"], "SITI AMINAH")
        self.assertEqual(mapped["alamat_ktp"], "Jl. Kenanga")
        self.assertEqual(mapped["jenis_kelamin"], "PEREMPUAN")
        self.assertEqual(mapped["agama"], "KRISTEN")
        self.assertEqual(mapped["tempat_lahir"], "BANDUNG")
        self.assertEqual(mapped["tanggal_lahir"], "1990-05-17")

    def test_map_extracted_data_date_formats(self):
        # DD-MM-YYYY format
        self.assertEqual(
            map_extracted_data({"tanggal_lahir": "05-08-1995"})["tanggal_lahir"],
            "1995-08-05",
        )
        # DD/MM/YYYY format
        self.assertEqual(
            map_extracted_data({"tanggal_lahir": "22/11/1988"})["tanggal_lahir"],
            "1988-11-22",
        )
        # YYYY-MM-DD format
        self.assertEqual(
            map_extracted_data({"tanggal_lahir": "2001-02-28"})["tanggal_lahir"],
            "2001-02-28",
        )
        # Single digit padding check
        self.assertEqual(
            map_extracted_data({"tanggal_lahir": "5-6-1990"})["tanggal_lahir"],
            "1990-06-05",
        )
        # Invalid format fallback
        self.assertEqual(
            map_extracted_data({"tanggal_lahir": "someday in 1990"})["tanggal_lahir"],
            "",
        )


class AIServiceTestCase(TestCase):
    @patch("requests.post")
    @override_settings(
        OLLAMA_API_URL="http://ollama-test:11434",
        OLLAMA_MODEL="test-vision",
        OLLAMA_API_KEY=None,
    )
    def test_ollama_provider_extract(self, mock_post):
        # Mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "message": {
                "content": '```json\n{"nik": "123", "nama": "Budi", "alamat_ktp": "Jl. A", "jenis_kelamin": "Laki", "agama": "Islam"}\n```'
            }
        }
        mock_post.return_value = mock_response

        provider = OllamaProvider()
        result = provider.extract_ktp_data(b"fake_image_bytes")

        self.assertEqual(result["nik"], "123")
        self.assertEqual(result["nama_lengkap"], "Budi")
        self.assertEqual(result["jenis_kelamin"], "LAKI-LAKI")
        self.assertEqual(result["agama"], "ISLAM")

        # Verify post payload
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertEqual(args[0], "http://ollama-test:11434/api/chat")
        self.assertEqual(kwargs["json"]["model"], "test-vision")
        self.assertIn("images", kwargs["json"]["messages"][0])
        self.assertNotIn("Authorization", kwargs.get("headers", {}))

    @patch("requests.post")
    @override_settings(
        OLLAMA_API_URL="http://ollama-test:11434",
        OLLAMA_MODEL="test-vision",
        OLLAMA_API_KEY="test-ollama-cloud-key",
    )
    def test_ollama_provider_extract_with_api_key(self, mock_post):
        # Mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "message": {
                "content": '{"nik": "123", "nama": "Budi", "alamat_ktp": "Jl. A", "jenis_kelamin": "Laki", "agama": "Islam"}'
            }
        }
        mock_post.return_value = mock_response

        provider = OllamaProvider()
        result = provider.extract_ktp_data(b"fake_image_bytes")

        self.assertEqual(result["nik"], "123")
        self.assertEqual(result["nama_lengkap"], "Budi")

        # Verify post payload includes Authorization header
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertEqual(args[0], "http://ollama-test:11434/api/chat")
        self.assertEqual(
            kwargs["headers"]["Authorization"], "Bearer test-ollama-cloud-key"
        )

    @patch("requests.post")
    @override_settings(
        OPENROUTER_API_KEY="test_openrouter_key", OPENROUTER_MODEL="google/test-flash"
    )
    def test_openrouter_provider_extract(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [
                {
                    "message": {
                        "content": '{"nik": "999", "nama": "Santi", "alamat_ktp": "Jl. B", "jenis_kelamin": "Wanita", "agama": "Kristen"}'
                    }
                }
            ]
        }
        mock_post.return_value = mock_response

        provider = OpenRouterProvider()
        result = provider.extract_ktp_data(b"fake_bytes")

        self.assertEqual(result["nik"], "999")
        self.assertEqual(result["nama_lengkap"], "Santi")
        self.assertEqual(result["jenis_kelamin"], "PEREMPUAN")
        self.assertEqual(result["agama"], "KRISTEN")

        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertEqual(args[0], "https://openrouter.ai/api/v1/chat/completions")
        self.assertEqual(
            kwargs["headers"]["Authorization"], "Bearer test_openrouter_key"
        )
        self.assertEqual(kwargs["json"]["model"], "google/test-flash")

    @patch("requests.get")
    @override_settings(OPENROUTER_API_KEY="test_openrouter_key")
    def test_openrouter_quota(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": {"limit_remaining": 0.50}}
        mock_get.return_value = mock_response

        provider = OpenRouterProvider()
        quota = provider.get_remaining_quota()
        self.assertEqual(quota, 0.50)
        self.assertTrue(provider.is_quota_low())

        # Test when limit_remaining is null but usage & limit are present
        mock_response.json.return_value = {
            "data": {"limit_remaining": None, "limit": 10.0, "usage": 8.5}
        }
        quota2 = provider.get_remaining_quota()
        self.assertEqual(quota2, 1.5)
        self.assertFalse(provider.is_quota_low())

    @override_settings(KTP_AI_PROVIDER="openrouter")
    def test_get_ai_provider_openrouter(self):
        provider = get_ai_provider()
        self.assertIsInstance(provider, OpenRouterProvider)

    @override_settings(KTP_AI_PROVIDER="ollama")
    def test_get_ai_provider_ollama(self):
        provider = get_ai_provider()
        self.assertIsInstance(provider, OllamaProvider)


class KTPScanViewTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="admin", password="password", is_staff=True
        )
        self.client.login(username="admin", password="password")

        # Create a Kompleks for test warga
        self.kompleks = Kompleks.objects.create(
            alamat="Jl. Test Map", blok="A1", nomor="1", rt="01", rw="02"
        )

        # Create warga
        self.warga = Warga.objects.create(
            nama_lengkap="Budi",
            nik="1234567890123456",
            alamat_ktp="Jl. Asli",
            jenis_kelamin="LAKI-LAKI",
            agama="ISLAM",
            kompleks=self.kompleks,
            status_tinggal="KONTRAK",
        )

    @patch("kependudukan.ai.ai_service.OllamaProvider.extract_ktp_data")
    @patch("kependudukan.ai.ai_service.OllamaProvider.is_quota_low")
    def test_scan_ktp_view_with_uploaded_file(self, mock_quota, mock_extract):
        mock_quota.return_value = False
        mock_extract.return_value = {
            "nik": "1111222233334444",
            "nama_lengkap": "SCAN SUCCESS",
            "alamat_ktp": "Jl. AI Result",
            "jenis_kelamin": "PEREMPUAN",
            "agama": "KRISTEN",
            "tempat_lahir": "BANDUNG",
            "tanggal_lahir": "1995-08-05",
        }

        # Make a dummy png image to upload
        im = Image.new("RGB", (100, 100), (0, 255, 0))
        im_io = io.BytesIO()
        im.save(im_io, "PNG")
        uploaded_file = SimpleUploadedFile(
            "ktp.png", im_io.getvalue(), content_type="image/png"
        )

        url = reverse("kependudukan:scan_ktp_ajax")
        response = self.client.post(url, {"ktp_image": uploaded_file})

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["data"]["nik"], "1111222233334444")
        self.assertEqual(data["data"]["nama_lengkap"], "SCAN SUCCESS")
        self.assertEqual(data["data"]["tempat_lahir"], "BANDUNG")
        self.assertEqual(data["data"]["tanggal_lahir"], "1995-08-05")
        self.assertFalse(data["quota_warning"])

    @patch("kependudukan.ai.ai_service.OllamaProvider.extract_ktp_data")
    def test_scan_ktp_view_with_existing_warga_no_image(self, mock_extract):
        url = reverse("kependudukan:scan_ktp_ajax")
        response = self.client.post(url, {"idwarga": self.warga.id})

        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertFalse(data["success"])
        self.assertIn("Pilih file foto KTP terlebih dahulu", data["message"])

    def test_scan_ktp_view_missing_arguments(self):
        url = reverse("kependudukan:scan_ktp_ajax")
        response = self.client.post(url, {})

        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertFalse(data["success"])
