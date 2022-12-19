from django.test import TestCase
from .models import Warga
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
        self.test_pass = ''.join(random.choices(string.ascii_lowercase, k=25))
        self.user = User.objects.create_user(username=self.test_user, password=self.test_pass, is_staff=True)
        Warga.objects.create(nama_lengkap=self.test_nama_lengkap, nik=self.test_nik)

    def test_select_warga(self):
        test_warga = Warga.objects.get(nama_lengkap="TestCase1")
        self.assertEqual(test_warga.nik, self.test_nik)

    def test_index_logged(self):
        client = Client()
        client.login(username=self.test_user, password=self.test_pass)
        response = client.get(reverse('kependudukan:index'))
        self.assertEqual(response.status_code, 200)

    def test_index(self):
        client = Client()
        response = client.get(reverse('kependudukan:index'))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/accounts/login/?next=/')
    