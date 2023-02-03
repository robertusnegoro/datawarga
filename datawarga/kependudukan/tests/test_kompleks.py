from django.test import TestCase
from ..models import Kompleks
from ..forms import GenerateKompleksForm
from django.contrib.auth.models import User
from datetime import datetime
from django.test import Client
from django.urls import reverse
import random
import string

class KompleksTestCase(TestCase):
    def setUp(self):
        self.test_user = "testuser"
        self.test_pass = "".join(random.choices(string.ascii_lowercase, k=25))
        self.user = User.objects.create_user(
            username=self.test_user, password=self.test_pass, is_staff=True
        )

        self.existing_kompleks = Kompleks.objects.create(
            alamat = "fake address",
            cluster = "fake cluster",
            blok = "J2",
            nomor = "5",
            rt = "001",
            rw = "002"
        )
    
    def test_generate_kompleks_form(self):
        form_data = {
            "alamat": "Fake alamat",
            "kecamatan": "test kecamatan",
            "kelurahan": "test kelurahan",
            "kota": "test kota",
            "provinsi" : "props",
            "kode_pos": "123122",
            "cluster": "test cluster",
            "blok": "A",
            "nomor": "2",
            "rt": "001",
            "rw": "003",
            "start_num": 5,
            "finish_num": 10
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
            "provinsi" : "props",
            "kode_pos": "123122",
            "cluster": "test cluster",
            "blok": "A",
            "nomor": "3",
            "rt": "001",
            "rw": "003",
            "start_num": 5,
            "finish_num": 10
        }
        response = client.post(reverse("kependudukan:generateKompleks"), data=form_data)
        self.assertEqual(response.status_code, 302)
        resp_url = response.url.split("?")[0]
        self.assertEqual(resp_url, reverse("kependudukan:listKompleksView"))