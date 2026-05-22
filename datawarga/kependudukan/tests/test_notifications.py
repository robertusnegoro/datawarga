from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from django.contrib.messages import get_messages
from ..models import (
    Warga,
    Kompleks,
    WargaPermissionGroup,
    TransaksiIuranBulanan,
    UserPermission,
    Surat,
    Penandatangan,
)
import random
import string


class NotificationsTestCase(TestCase):
    def setUp(self):
        self.test_user = "testuser"
        self.test_pass = "".join(random.choices(string.ascii_lowercase, k=25))
        self.user = User.objects.create_user(
            username=self.test_user, password=self.test_pass, is_staff=True
        )
        self.group = WargaPermissionGroup.objects.create(group_name="all")
        self.permission = UserPermission.objects.create(
            user=self.user, permission_group=self.group
        )

        self.kompleks = Kompleks.objects.create(
            alamat="fake address",
            cluster="fake cluster",
            blok="J2",
            nomor="5",
            rt="001",
            rw="002",
            permission_group=self.group,
        )

        self.warga = Warga.objects.create(
            nama_lengkap="John Doe",
            nik="1234567890",
            kompleks=self.kompleks,
        )

        self.penandatangan = Penandatangan.objects.create(
            nama="Pak RT",
            jabatan="Ketua RT",
            aktif=True,
        )

    def test_delete_surat_without_next(self):
        surat = Surat.objects.create(
            warga=self.warga,
            jenis_surat="PENGANTAR_RT",
            keperluan="Bikin KTP",
            penandatangan=self.penandatangan,
        )

        client = Client()
        client.login(username=self.test_user, password=self.test_pass)

        # GET request to delete confirmation page
        response = client.get(
            reverse("kependudukan:delete_surat", kwargs={"idsurat": surat.id})
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "surat/delete_surat.html")

        # POST request to delete the letter
        response = client.post(
            reverse("kependudukan:delete_surat", kwargs={"idsurat": surat.id})
        )
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(
            response,
            reverse("kependudukan:detailWarga", kwargs={"idwarga": self.warga.id}),
        )

        # Verify deletion from DB
        with self.assertRaises(Surat.DoesNotExist):
            Surat.objects.get(pk=surat.id)

        # Verify flash message
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertIn("Surat Pengantar RT", str(messages[0]))
        self.assertIn("berhasil dihapus", str(messages[0]))

    def test_delete_surat_with_next_list(self):
        surat = Surat.objects.create(
            warga=self.warga,
            jenis_surat="KETERANGAN_DOMISILI",
            keperluan="Domisili usaha",
            penandatangan=self.penandatangan,
        )

        client = Client()
        client.login(username=self.test_user, password=self.test_pass)

        # POST request with next parameter
        response = client.post(
            reverse("kependudukan:delete_surat", kwargs={"idsurat": surat.id})
            + "?next=list_surat"
        )
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("kependudukan:list_surat"))

        # Verify deletion from DB
        with self.assertRaises(Surat.DoesNotExist):
            Surat.objects.get(pk=surat.id)

        # Verify flash message
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertIn("Surat Keterangan Domisili", str(messages[0]))

    def test_generate_kompleks_flash_message(self):
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
            "permission_group": self.group.id,
        }

        response = client.post(reverse("kependudukan:generateKompleks"), data=form_data)
        self.assertEqual(response.status_code, 302)

        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertIn("Data blok <strong>A</strong>", str(messages[0]))
        self.assertIn("nomor rumah telah disimpan", str(messages[0]))

    def test_delete_blok_flash_message(self):
        # Create block A complexes
        Kompleks.objects.create(
            cluster="test cluster",
            blok="A",
            nomor="1",
            rt="001",
            rw="002",
            permission_group=self.group,
        )
        Kompleks.objects.create(
            cluster="test cluster",
            blok="A",
            nomor="2",
            rt="001",
            rw="002",
            permission_group=self.group,
        )

        client = Client()
        client.login(username=self.test_user, password=self.test_pass)

        response = client.post(
            reverse("kependudukan:deleteBlokForm"), data={"blok": "A"}
        )
        self.assertEqual(response.status_code, 302)

        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertIn(
            "Data blok <strong>A</strong> sebanyak <strong>2</strong> nomor rumah telah dihapus",
            str(messages[0]),
        )

        # Verify deletion from DB
        self.assertEqual(Kompleks.objects.filter(blok="A").count(), 0)

    def test_detail_kompleks_edit_flash_message(self):
        client = Client()
        client.login(username=self.test_user, password=self.test_pass)

        form_data = {
            "cluster": "updated cluster",
            "blok": "J2",
            "nomor": "99",
            "rt": "001",
            "rw": "002",
            "description": "updated desc",
            "alamat": "updated address",
            "kecamatan": "Setu",
            "kelurahan": "Babakan",
            "kota": "Tangsel",
            "provinsi": "Banten",
            "kode_pos": "12345",
        }

        response = client.post(
            reverse(
                "kependudukan:detailKompleks", kwargs={"idkompleks": self.kompleks.id}
            ),
            data=form_data,
        )
        self.assertEqual(response.status_code, 200)

        # Verify db updated
        self.kompleks.refresh_from_db()
        self.assertEqual(self.kompleks.nomor, "99")

        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertIn("Data <strong>J2/99</strong> berhasil disimpan", str(messages[0]))

    def test_delete_rumah_flash_message(self):
        client = Client()
        client.login(username=self.test_user, password=self.test_pass)

        response = client.post(
            reverse(
                "kependudukan:deleteRumahForm", kwargs={"idkompleks": self.kompleks.id}
            ),
            data={"idkompleks": self.kompleks.id},
        )
        self.assertEqual(response.status_code, 302)

        # Verify db updated
        with self.assertRaises(Kompleks.DoesNotExist):
            Kompleks.objects.get(pk=self.kompleks.id)

        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertIn(
            "Data rumah <strong>J2 / 5</strong> berhasil dihapus", str(messages[0])
        )

    def test_form_iuran_bulanan_save_flash_message(self):
        client = Client()
        client.login(username=self.test_user, password=self.test_pass)

        form_data = {
            "kompleks": self.kompleks.id,
            "periode_bulan": 1,
            "periode_tahun": 2026,
            "total_bayar": 100000,
            "keterangan": "Iuran Januari",
        }

        response = client.post(
            reverse("kependudukan:formIuranBulananSave"), data=form_data
        )
        self.assertEqual(response.status_code, 302)

        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertIn("Iuran bulanan berhasil disimpan", str(messages[0]))

    def test_delete_iuran_bulanan_flash_message(self):
        iuran_rec = TransaksiIuranBulanan.objects.create(
            kompleks=self.kompleks,
            periode_bulan=5,
            periode_tahun=2026,
            total_bayar=100000,
            keterangan="Iuran Mei",
        )

        client = Client()
        client.login(username=self.test_user, password=self.test_pass)

        response = client.post(
            reverse(
                "kependudukan:deleteIuranBulanan", kwargs={"idtransaksi": iuran_rec.id}
            ),
            data={"idtransaksi": iuran_rec.id},
        )
        self.assertEqual(response.status_code, 302)

        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertIn(
            "Iuran bulanan untuk bulan <strong>Mei 2026</strong> berhasil dihapus",
            str(messages[0]),
        )

    def test_batch_iuran_bulanan_flash_message(self):
        client = Client()
        client.login(username=self.test_user, password=self.test_pass)

        form_data = {
            "bulan": [1, 2, 3],
            "periode_tahun": 2026,
            "total_bayar": 100000,
            "keterangan": "Batch Q1",
        }

        response = client.post(
            reverse(
                "kependudukan:batchIuranBulanan",
                kwargs={"idkompleks": self.kompleks.id, "year": "2026"},
            ),
            data=form_data,
        )
        self.assertEqual(response.status_code, 302)

        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertIn(
            "Iuran bulanan untuk <strong>3</strong> bulan berhasil disimpan",
            str(messages[0]),
        )
