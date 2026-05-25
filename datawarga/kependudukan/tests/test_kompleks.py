from django.test import TestCase
from ..models import Kompleks, WargaPermissionGroup, TransaksiIuranBulanan
from ..forms import GenerateKompleksForm
from django.contrib.auth.models import User
from django.test import Client
from django.urls import reverse
import random
import string
from unittest.mock import patch


class KompleksTestCase(TestCase):
    def setUp(self):
        self.test_user = "testuser"
        self.test_pass = "".join(random.choices(string.ascii_lowercase, k=25))
        self.user = User.objects.create_user(
            username=self.test_user, password=self.test_pass, is_staff=True
        )

        self.existing_kompleks = Kompleks.objects.create(
            alamat="fake address",
            cluster="fake cluster",
            blok="J2",
            nomor="5",
            rt="001",
            rw="002",
        )

    def test_generate_kompleks_form(self):
        form_data = {
            "alamat": "Fake alamat",
            "kecamatan": "test kecamatan",
            "kelurahan": "test kelurahan",
            "kota": "test kota",
            "provinsi": "props",
            "kode_pos": "123122",
            "cluster": "test cluster",
            "blok": "A",
            "nomor": "2",
            "rt": "001",
            "rw": "003",
            "start_num": 5,
            "finish_num": 10,
        }

        form = GenerateKompleksForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_generate_kompleks_exec(self):
        client = Client()
        client.login(username=self.test_user, password=self.test_pass)
        form_data = {
            "alamat": "Fake alamat",
            "kecamatan": "test kecamatan",
            "kelurahan": "test kelurahan",
            "kota": "test kota",
            "provinsi": "props",
            "kode_pos": "123122",
            "cluster": "test cluster",
            "blok": "A",
            "nomor": "3",
            "rt": "001",
            "rw": "003",
            "start_num": 5,
            "finish_num": 10,
            "permission_group": "1",
        }

        # Create and save a real permission group for the test
        permission_group = WargaPermissionGroup.objects.create()
        permission_group.save()

        # Mock the permission group lookup to return our saved instance
        with patch("kependudukan.models.WargaPermissionGroup.objects.get") as mock_get:
            mock_get.return_value = permission_group
            response = client.post(
                reverse("kependudukan:generateKompleks"), data=form_data
            )
            self.assertEqual(response.status_code, 302)
            resp_url = response.url.split("?")[0]
            self.assertEqual(resp_url, reverse("kependudukan:listKompleksView"))

    def test_kompleks_str(self):
        """Test the string representation of Kompleks"""
        self.assertEqual(str(self.existing_kompleks), "J2 / 5")

    def test_generate_kompleks_form_invalid(self):
        """Test invalid form data"""
        form_data = {
            "blok": "",  # Required field
            "rt": "001",
            "rw": "003",
            "start_num": 5,
            "finish_num": 10,
        }

        form = GenerateKompleksForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn("blok", form.errors)

    def test_generate_kompleks_limit_exceeded(self):
        """Test generating more kompleks than allowed"""
        client = Client()
        client.login(username=self.test_user, password=self.test_pass)

        form_data = {
            "alamat": "Test alamat",
            "kecamatan": "test kecamatan",
            "kelurahan": "test kelurahan",
            "kota": "test kota",
            "provinsi": "test provinsi",
            "kode_pos": "123122",
            "cluster": "test cluster",
            "blok": "X",
            "rt": "001",
            "rw": "003",
            "start_num": 1,
            "finish_num": 1000,
            "nomor": "1",
            "permission_group": "1",
        }

        # Create and save a real permission group for the test
        permission_group = WargaPermissionGroup.objects.create()
        permission_group.save()

        # Mock the permission group lookup
        with patch("kependudukan.models.WargaPermissionGroup.objects.get") as mock_get:
            mock_get.return_value = permission_group
            response = client.post(
                reverse("kependudukan:generateKompleks"), data=form_data
            )
            self.assertContains(
                response,
                "Error. User seharusnya tidak mengenerate lebih dari 200 nomor rumah",
            )

    def test_kompleks_detail_not_found(self):
        """Test accessing non-existent kompleks"""
        client = Client()
        client.login(username=self.test_user, password=self.test_pass)

        response = client.get(
            reverse("kependudukan:detailKompleks", kwargs={"idkompleks": 99999})
        )
        self.assertEqual(response.status_code, 404)

    def test_delete_kompleks(self):
        """Test deleting a kompleks"""
        client = Client()
        client.login(username=self.test_user, password=self.test_pass)

        # Create kompleks to delete
        kompleks = Kompleks.objects.create(
            alamat="delete test",
            cluster="test cluster",
            blok="Z9",
            nomor="99",
            rt="001",
            rw="002",
        )

        # First get the confirmation page
        response = client.get(
            reverse("kependudukan:deleteRumahForm", kwargs={"idkompleks": kompleks.id})
        )
        self.assertEqual(response.status_code, 200)

        # Then submit the deletion form
        response = client.post(
            reverse("kependudukan:deleteRumahForm", kwargs={"idkompleks": kompleks.id}),
            data={"idkompleks": kompleks.id},
        )
        self.assertEqual(response.status_code, 302)  # Should redirect after deletion

        # Verify deletion
        with self.assertRaises(Kompleks.DoesNotExist):
            Kompleks.objects.get(id=kompleks.id)

    def test_form_iuran_bulanan_formatting(self):
        """Test that formIuranBulanan view displays money values with thousand separator"""
        client = Client()
        client.login(username=self.test_user, password=self.test_pass)

        # Create a TransaksiIuranBulanan with total_bayar = 150000
        TransaksiIuranBulanan.objects.create(
            kompleks=self.existing_kompleks,
            periode_bulan=5,
            periode_tahun=2026,
            total_bayar=150000,
            keterangan="Iuran bulanan May 2026",
        )

        response = client.get(
            reverse(
                "kependudukan:formIuranBulananYear",
                kwargs={"idkompleks": self.existing_kompleks.id, "year": 2026},
            )
        )
        self.assertEqual(response.status_code, 200)
        # Verify that total_bayar is formatted as Rp 150.000 in the HTML template output
        self.assertContains(response, "Rp 150.000")

    def test_list_kompleks_json_endpoint(self):
        """Test list_kompleks_json returns complexes with their active residents"""
        from ..models import Warga, UserPermission, WargaPermissionGroup

        client = Client()
        client.login(username=self.test_user, password=self.test_pass)

        # Ensure user permission group allows viewing
        group_all = WargaPermissionGroup.objects.create(group_name="All")
        UserPermission.objects.create(user=self.user, permission_group=group_all)

        # Create a citizen in our existing kompleks
        Warga.objects.create(
            nama_lengkap="Test Resident",
            nik="1234567890123456",
            kompleks=self.existing_kompleks,
            status_tinggal="TETAP",
            status_keluarga="SUAMI",
            kepala_keluarga=True,
            tanggal_lahir="1990-01-01",
        )

        response = client.get(reverse("kependudukan:listKompleksJson"))
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertIn("data", data)
        self.assertTrue(len(data["data"]) > 0)

        # Find self.existing_kompleks in the list
        matched_item = None
        for item in data["data"]:
            if item["pk"] == self.existing_kompleks.id:
                matched_item = item
                break

        self.assertIsNotNone(matched_item)
        self.assertEqual(matched_item["fields"]["blok"], "J2")
        self.assertEqual(matched_item["fields"]["nomor"], "5")

        # Check residents list
        residents = matched_item["fields"]["residents"]
        self.assertEqual(len(residents), 1)
        self.assertEqual(residents[0]["nama_lengkap"], "Test Resident")
        self.assertEqual(residents[0]["status_keluarga"], "SUAMI")
        self.assertTrue(residents[0]["kepala_keluarga"])
