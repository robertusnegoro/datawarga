from django.test import TestCase
from .models import Warga
from datetime import datetime

# Create your tests here.


class WargaTestCase(TestCase):
    def setUp(self):
        self.test_nama_lengkap = "TestCase1"
        self.test_nik = "nik_test_case1"
        Warga.objects.create(nama_lengkap=self.test_nama_lengkap, nik=self.test_nik)

    def test_select_warga(self):
        test_warga = Warga.objects.get(nama_lengkap="TestCase1")
        self.assertEqual(test_warga.nik, self.test_nik)
