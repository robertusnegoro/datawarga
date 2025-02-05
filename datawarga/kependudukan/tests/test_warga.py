from django.test import TestCase
from ..models import Warga, Kompleks
from ..forms import WargaForm
from django.contrib.auth.models import User
from datetime import datetime
from django.test import Client
from django.urls import reverse
import random
import string
from django.utils.timezone import now
from datetime import timedelta

# Create your tests here.


class WargaTestCase(TestCase):
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

        self.test_nama_lengkap = "TestCase1"
        self.test_nik = "nik_test_case1"
        self.existing_warga = Warga.objects.create(
            nama_lengkap=self.test_nama_lengkap,
            nik=self.test_nik,
            kompleks=self.existing_kompleks,
        )

    def test_select_warga(self):
        test_warga = Warga.objects.get(nama_lengkap="TestCase1")
        self.assertEqual(test_warga.nik, self.test_nik)

    def test_form_warga_valid(self):
        form_data = {
            "nama_lengkap": "test nama",
            "nik": "123123123",
            "agama": "ISLAM",
            "no_hp": "08123456789",
            "alamat": "jalan alamat",
            "kecamatan": "Setu",
            "kelurahan": "Babakan",
            "kota": "Tangsel",
            "provinsi": "Banten",
            "pekerjaan": "PNS",
            "tanggal_lahir": "1990-01-01",
            "status": "BELUM KAWIN",
            "jenis_kelamin": "PEREMPUAN",
            "status_tinggal": "KONTRAK",
            "kompleks": self.existing_kompleks.id,
            "status_keluarga": "SAUDARA",
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
            "status_keluarga": "SAUDARA",
        }
        form = WargaForm(data=form_data)
        self.assertFalse(form.is_valid())

    def test_index_logged(self):
        client = Client()
        client.login(username=self.test_user, password=self.test_pass)
        response = client.get(reverse("kependudukan:index"))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("kependudukan:dashboardWarga"))

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
            "agama": "BUDDHA",
            "no_hp": "08123456789",
            "alamat": "jalan alamat",
            "kecamatan": "Setu",
            "kelurahan": "Babakan",
            "kota": "Tangsel",
            "provinsi": "Banten",
            "pekerjaan": "PNS",
            "tanggal_lahir": "1990-01-01",
            "status": "BELUM KAWIN",
            "jenis_kelamin": "PEREMPUAN",
            "status_tinggal": "KONTRAK",
            "kompleks": self.existing_kompleks.id,
            "status_keluarga": "SAUDARA",
        }
        response = client.post(reverse("kependudukan:formWargaSimpan"), data=form_data)
        self.assertEqual(response.status_code, 302)
        resp_url = response.url.split("?")[0]
        self.assertEqual(resp_url, reverse("kependudukan:listWargaView"))

    def test_form_update(self):
        client = Client()
        client.login(username=self.test_user, password=self.test_pass)
        form_data = {
            "idwarga": self.existing_warga.id,
            "nama_lengkap": self.test_nama_lengkap,
            "nik": self.test_nik,
            "agama": "ISLAM",
            "no_hp": "089876543",
            "alamat": "jalan alamat",
            "kecamatan": "Setu",
            "kelurahan": "Babakan",
            "kota": "Tangsel",
            "provinsi": "Banten",
            "pekerjaan": "PNS",
            "tanggal_lahir": "1990-01-01",
            "status": "BELUM KAWIN",
            "jenis_kelamin": "PEREMPUAN",
            "status_tinggal": "KONTRAK",
            "kompleks": self.existing_kompleks.id,
            "status_keluarga": "SAUDARA",
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

    def test_statistic_warga(self):
        client = Client()
        client.login(username=self.test_user, password=self.test_pass)
        
        # Create test data
        warga2 = Warga.objects.create(
            nama_lengkap="Test Stats 2",
            nik="stats_test_2",
            kompleks=self.existing_kompleks,
            agama="ISLAM",
            jenis_kelamin="LAKI-LAKI",
            status_tinggal="TETAP"
        )
        
        response = client.get(reverse("kependudukan:statisticWarga"))
        self.assertEqual(response.status_code, 200)
        
        # Test context data
        self.assertIn('all_data', response.context)
        self.assertIn('jenis_kelamin', response.context)
        self.assertIn('agama', response.context)
        self.assertIn('status_tinggal', response.context)
        
        # Verify counts
        all_data = response.context['all_data']
        self.assertEqual(all_data[0]['num_warga'], 2)  # Should count both test warga

    def test_warga_age_filters(self):
        today = now().date()
        
        # Create elderly person (>55 years)
        elderly = Warga.objects.create(
            nama_lengkap="Test Elderly",
            nik="elderly_test",
            kompleks=self.existing_kompleks,
            tanggal_lahir=today - timedelta(days=56*365),
            agama="ISLAM",
            jenis_kelamin="LAKI-LAKI",
            status_tinggal="TETAP"
        )
        
        # Create child (<5 years)
        child = Warga.objects.create(
            nama_lengkap="Test Child", 
            nik="child_test",
            kompleks=self.existing_kompleks,
            tanggal_lahir=today - timedelta(days=3*365),
            agama="ISLAM",
            jenis_kelamin="LAKI-LAKI",
            status_tinggal="TETAP"
        )
        
        client = Client()
        client.login(username=self.test_user, password=self.test_pass)
        
        # Test elderly filter
        response = client.post(reverse("kependudukan:pdfWargaReport"), {
            'file_type': 'pdf',
            'cluster': 'all',
            'status_tinggal': 'ALL',
            'rt': '',
            'usia': 'lansia'
        })
        self.assertEqual(response.status_code, 200)
        
        # Test child filter  
        response = client.post(reverse("kependudukan:pdfWargaReport"), {
            'file_type': 'pdf',
            'cluster': 'all', 
            'status_tinggal': 'ALL',
            'rt': '',
            'usia': 'balita'
        })
        self.assertEqual(response.status_code, 200)

    def test_warga_moved_out(self):
        # Create warga who moved out
        moved_warga = Warga.objects.create(
            nama_lengkap="Test Moved",
            nik="moved_test",
            kompleks=self.existing_kompleks,
            status_tinggal="PINDAH",
            agama="ISLAM",
            jenis_kelamin="LAKI-LAKI"
        )
        
        client = Client()
        client.login(username=self.test_user, password=self.test_pass)
        
        response = client.get(reverse("kependudukan:statisticWarga"))
        self.assertEqual(response.status_code, 200)
        
        # Verify moved warga is excluded from main stats
        all_data = response.context['all_data']
        self.assertEqual(all_data[0]['num_warga'], 1)  # Should only count non-moved warga
