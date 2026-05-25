from django.test import TestCase
from kependudukan.models import Warga, Kompleks
from kependudukan.selectors.warga_selector import search_warga_queryset
from kependudukan.selectors.kompleks_selector import search_kompleks_queryset


class WargaSelectorTests(TestCase):
    def setUp(self):
        self.kompleks = Kompleks.objects.create(
            cluster="Test", blok="A", nomor="1", rt="01", rw="01"
        )
        self.warga1 = Warga.objects.create(
            nama_lengkap="John Doe", nik="123", kompleks=self.kompleks
        )
        self.warga2 = Warga.objects.create(
            nama_lengkap="Jane Doe", nik="124", kompleks=self.kompleks
        )

    def test_search_warga_queryset(self):
        qs = Warga.objects.all()
        result = search_warga_queryset(qs, "John")
        self.assertEqual(result.count(), 1)
        self.assertEqual(result.first().nama_lengkap, "John Doe")

    def test_search_warga_queryset_blok(self):
        qs = Warga.objects.all()
        result = search_warga_queryset(qs, "A / 1")
        self.assertEqual(result.count(), 2)


class KompleksSelectorTests(TestCase):
    def setUp(self):
        self.kompleks1 = Kompleks.objects.create(
            cluster="Test A", blok="A", nomor="1", rt="01", rw="01"
        )
        self.kompleks2 = Kompleks.objects.create(
            cluster="Test B", blok="B", nomor="2", rt="01", rw="01"
        )

    def test_search_kompleks_queryset(self):
        qs = Kompleks.objects.all()
        result = search_kompleks_queryset(qs, "Test A")
        self.assertEqual(result.count(), 1)
        self.assertEqual(result.first().cluster, "Test A")

    def test_search_kompleks_queryset_blok(self):
        qs = Kompleks.objects.all()
        result = search_kompleks_queryset(qs, "B / 2")
        self.assertEqual(result.count(), 1)
        self.assertEqual(result.first().blok, "B")
