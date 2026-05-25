from django.test import TestCase
from kependudukan.models import Warga, Kompleks
from kependudukan.services.warga_service import assign_kepala_keluarga
from kependudukan.services.iuran_service import record_iuran_payment
from kependudukan.errors import NotFoundError, DatawargaError


class WargaServiceTests(TestCase):
    def setUp(self):
        self.kompleks = Kompleks.objects.create(
            cluster="Test", blok="A", nomor="1", rt="01", rw="01"
        )
        self.warga1 = Warga.objects.create(
            nama_lengkap="John Doe",
            nik="123",
            kompleks=self.kompleks,
            kepala_keluarga=False,
        )
        self.warga2 = Warga.objects.create(
            nama_lengkap="Jane Doe",
            nik="124",
            kompleks=self.kompleks,
            kepala_keluarga=True,
        )

    def test_assign_kepala_keluarga(self):
        warga = assign_kepala_keluarga(self.warga1.id)

        self.warga1.refresh_from_db()
        self.warga2.refresh_from_db()

        self.assertTrue(self.warga1.kepala_keluarga)
        self.assertFalse(self.warga2.kepala_keluarga)
        self.assertEqual(warga, self.warga1)


class IuranServiceTests(TestCase):
    def setUp(self):
        self.kompleks = Kompleks.objects.create(
            cluster="Test", blok="B", nomor="1", rt="01", rw="01"
        )

    def test_record_iuran_payment(self):
        payment = record_iuran_payment("B/1", "1", "2023", "100000", None)
        self.assertEqual(payment.kompleks, self.kompleks)
        self.assertEqual(payment.periode_bulan, "1")
        self.assertEqual(payment.periode_tahun, "2023")
        self.assertEqual(payment.total_bayar, "100000")

    def test_record_iuran_payment_invalid_blok(self):
        with self.assertRaises(DatawargaError):
            record_iuran_payment("Invalid", "1", "2023", "100000", None)

    def test_record_iuran_payment_not_found(self):
        with self.assertRaises(NotFoundError):
            record_iuran_payment("B/2", "1", "2023", "100000", None)

    def test_record_iuran_payment_duplicate(self):
        record_iuran_payment("B/1", "1", "2023", "100000", None)
        with self.assertRaises(DatawargaError):
            record_iuran_payment("B/1", "1", "2023", "100000", None)
