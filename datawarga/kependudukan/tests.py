from django.test import TestCase
from .models import Warga
from .forms import WargaForm
from django.contrib.auth.models import User
from datetime import datetime
from django.test import Client
from django.urls import reverse
import random
import string

# Create your tests here.


class WargaTestCase(TestCase):
    def setUp(self):
        self.test_nama_lengkap = "TestCase1"
        self.test_nik = "nik_test_case1"
        self.test_user = "testuser"
        self.test_pass = "".join(random.choices(string.ascii_lowercase, k=25))
        self.user = User.objects.create_user(
            username=self.test_user, password=self.test_pass, is_staff=True
        )
        self.existing_user = Warga.objects.create(
            nama_lengkap=self.test_nama_lengkap, nik=self.test_nik
        )

    def test_select_warga(self):
        test_warga = Warga.objects.get(nama_lengkap="TestCase1")
        self.assertEqual(test_warga.nik, self.test_nik)

    def test_form_warga_valid(self):
        form_data = {
            "nama_lengkap": "test nama",
            "nik": "123123123",
            "agama": "islam",
            "no_hp": "08123456789",
            "alamat": "jalan alamat",
            "kecamatan": "Setu",
            "kelurahan": "Babakan",
            "kota": "Tangsel",
            "provinsi": "Banten",
            "pekerjaan": "PNS",
            "tanggal_lahir": "1990-01-01",
            "status": "BELUM KAWIN",
            "jenis_kelamin": "Perempuan",
            "status_tinggal": "KONTRAK",
        }
        form = WargaForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_form_warga_invalid(self):
        form_data = {
            "nama_lengkap": "test nama",
        }
        form = WargaForm(data=form_data)
        self.assertFalse(form.is_valid())

    def test_form_warga_nik(self):
        form_data = {
            "nama_lengkap": "test nama",
            "nik": "nik_test_case1",
            "agama": "islam",
            "no_hp": "08123456789",
            "alamat": "jalan alamat",
            "kecamatan": "Setu",
            "kelurahan": "Babakan",
            "kota": "Tangsel",
            "provinsi": "Banten",
            "pekerjaan": "PNS",
            "tanggal_lahir": "1990-01-01",
            "status": "BELUM KAWIN",
            "jenis_kelamin": "Perempuan",
            "status_tinggal": "KONTRAK",
        }
        form = WargaForm(data=form_data)
        self.assertFalse(form.is_valid())

    def test_index_logged(self):
        client = Client()
        client.login(username=self.test_user, password=self.test_pass)
        response = client.get(reverse("kependudukan:index"))
        self.assertEqual(response.status_code, 200)

    def test_index(self):
        client = Client()
        response = client.get(reverse("kependudukan:index"))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/accounts/login/?next=/")

    def test_list_warga_unlogged(self):
        client = Client()
        response = client.get(reverse("kependudukan:listWargaView"))
        self.assertEqual(response.status_code, 302)

    def test_form_insert(self):
        client = Client()
        client.login(username=self.test_user, password=self.test_pass)
        form_data = {
            "nama_lengkap": "test case",
            "nik": "000000000",
            "agama": "buddha",
            "no_hp": "08123456789",
            "alamat": "jalan alamat",
            "kecamatan": "Setu",
            "kelurahan": "Babakan",
            "kota": "Tangsel",
            "provinsi": "Banten",
            "pekerjaan": "PNS",
            "tanggal_lahir": "1990-01-01",
            "status": "BELUM KAWIN",
            "jenis_kelamin": "Perempuan",
            "status_tinggal": "KONTRAK",
        }
        response = client.post(reverse("kependudukan:formWargaSimpan"), data=form_data)
        self.assertEqual(response.status_code, 302)
        resp_url = response.url.split("?")[0]
        self.assertEqual(resp_url, reverse("kependudukan:listWargaView"))

    def test_form_update(self):
        client = Client()
        client.login(username=self.test_user, password=self.test_pass)
        form_data = {
            "idwarga": self.existing_user.id,
            "nama_lengkap": self.test_nama_lengkap,
            "nik": self.test_nik,
            "agama": "buddha",
            "no_hp": "089876543",
            "alamat": "jalan alamat",
            "kecamatan": "Setu",
            "kelurahan": "Babakan",
            "kota": "Tangsel",
            "provinsi": "Banten",
            "pekerjaan": "PNS",
            "tanggal_lahir": "1990-01-01",
            "status": "BELUM KAWIN",
            "jenis_kelamin": "Perempuan",
            "status_tinggal": "KONTRAK",
        }
        response = client.post(reverse("kependudukan:formWargaSimpan"), data=form_data)
        self.assertEqual(response.status_code, 302)
        resp_url = response.url.split("?")[0]
        self.assertEqual(resp_url, reverse("kependudukan:listWargaView"))

    def test_delete_warga_notfound(self):
        client = Client()
        client.login(username=self.test_user, password=self.test_pass)
        delete_url = reverse("kependudukan:deleteformWarga", kwargs={"idwarga": 44999})
        response = client.get(delete_url)
        self.assertEqual(response.status_code, 404)

    def test_delete_warga_post(self):
        warga = Warga.objects.create(nama_lengkap="test delete", nik="999666000")
        client = Client()
        client.login(username=self.test_user, password=self.test_pass)
        delete_url = reverse(
            "kependudukan:deleteformWarga", kwargs={"idwarga": warga.id}
        )
        response = client.post(delete_url, data={"idwarga": warga.id})
        self.assertEqual(response.status_code, 302)
