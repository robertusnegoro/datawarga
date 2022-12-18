from django.test import TestCase
from .models import Warga
from django.contrib.auth.models import User
from datetime import datetime

# Create your tests here.


class WargaTestCase(TestCase):
    def setUp(self):
        self.test_nama_lengkap = "TestCase1"
        self.test_nik = "nik_test_case1"
        self.test_user = "testuser"
        self.test_pass = "testpass123321123"
        self.user = User.objects.create_user(username=self.test_user, password=self.test_pass)
        Warga.objects.create(nama_lengkap=self.test_nama_lengkap, nik=self.test_nik)

    def test_select_warga(self):
        test_warga = Warga.objects.get(nama_lengkap="TestCase1")
        self.assertEqual(test_warga.nik, self.test_nik)
