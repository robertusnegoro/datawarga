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
            status_tinggal="TETAP",
        )

        response = client.get(reverse("kependudukan:statisticWarga"))
        self.assertEqual(response.status_code, 200)

        # Test context data
        self.assertIn("all_data", response.context)
        self.assertIn("jenis_kelamin", response.context)
        self.assertIn("agama", response.context)
        self.assertIn("status_tinggal", response.context)

        # Verify counts
        all_data = response.context["all_data"]
        self.assertEqual(all_data[0]["num_warga"], 2)  # Should count both test warga

    def test_warga_age_filters(self):
        today = now().date()

        # Create elderly person (>55 years)
        elderly = Warga.objects.create(
            nama_lengkap="Test Elderly",
            nik="elderly_test",
            kompleks=self.existing_kompleks,
            tanggal_lahir=today - timedelta(days=56 * 365),
            agama="ISLAM",
            jenis_kelamin="LAKI-LAKI",
            status_tinggal="TETAP",
        )

        # Create child (<5 years)
        child = Warga.objects.create(
            nama_lengkap="Test Child",
            nik="child_test",
            kompleks=self.existing_kompleks,
            tanggal_lahir=today - timedelta(days=3 * 365),
            agama="ISLAM",
            jenis_kelamin="LAKI-LAKI",
            status_tinggal="TETAP",
        )

        client = Client()
        client.login(username=self.test_user, password=self.test_pass)

        # Test elderly filter
        response = client.post(
            reverse("kependudukan:pdfWargaReport"),
            {
                "file_type": "pdf",
                "cluster": "all",
                "status_tinggal": "ALL",
                "rt": "",
                "usia": "lansia",
            },
        )
        self.assertEqual(response.status_code, 200)

        # Test child filter
        response = client.post(
            reverse("kependudukan:pdfWargaReport"),
            {
                "file_type": "pdf",
                "cluster": "all",
                "status_tinggal": "ALL",
                "rt": "",
                "usia": "balita",
            },
        )
        self.assertEqual(response.status_code, 200)

    def test_warga_moved_out(self):
        # Create warga who moved out
        moved_warga = Warga.objects.create(
            nama_lengkap="Test Moved",
            nik="moved_test",
            kompleks=self.existing_kompleks,
            status_tinggal="PINDAH",
            agama="ISLAM",
            jenis_kelamin="LAKI-LAKI",
        )

        client = Client()
        client.login(username=self.test_user, password=self.test_pass)

        response = client.get(reverse("kependudukan:statisticWarga"))
        self.assertEqual(response.status_code, 200)

        # Verify moved warga is excluded from main stats
        all_data = response.context["all_data"]
        self.assertEqual(
            all_data[0]["num_warga"], 1
        )  # Should only count non-moved warga

    def test_dashboard_with_none_cluster(self):
        # Create a kompleks with cluster = None
        none_cluster_kompleks = Kompleks.objects.create(
            alamat="none cluster address",
            cluster=None,
            blok="N1",
            nomor="10",
            rt="001",
            rw="002",
        )
        # Create a resident in that kompleks
        Warga.objects.create(
            nama_lengkap="None Cluster Warga",
            nik="none_cluster_nik",
            kompleks=none_cluster_kompleks,
            status_tinggal="TETAP",
            agama="ISLAM",
            jenis_kelamin="LAKI-LAKI",
        )

        client = Client()
        client.login(username=self.test_user, password=self.test_pass)

        # Test main dashboard
        response = client.get(reverse("kependudukan:dashboardWarga"))
        self.assertEqual(response.status_code, 200)
        # Check that the mapped string "Tanpa Cluster" is present in the context and rendered page
        self.assertIn("Tanpa Cluster", response.context["legend_cluster"])
        self.assertContains(response, "Tanpa Cluster")

        # Test public cluster dashboard
        response_public = client.get(
            reverse("kependudukan:publicDasboard", kwargs={"page": "cluster"})
        )
        self.assertEqual(response_public.status_code, 200)
        self.assertIn("Tanpa Cluster", response_public.context["legend_cluster"])

    def test_daftar_kepala_keluarga_view(self):
        # Create user permission so user can list
        from ..models import UserPermission, WargaPermissionGroup

        group = WargaPermissionGroup.objects.create(group_name="all")
        UserPermission.objects.create(user=self.user, permission_group=group)

        # Create KK warga
        kk_warga = Warga.objects.create(
            nama_lengkap="Kepala Keluarga Test",
            nik="nik_kk_test",
            no_kk="12345",
            kompleks=self.existing_kompleks,
            kepala_keluarga=True,
            status_tinggal="TETAP",
        )
        # Create non-KK warga
        non_kk_warga = Warga.objects.create(
            nama_lengkap="Anggota Test",
            nik="nik_anggota_test",
            no_kk="12345",
            kompleks=self.existing_kompleks,
            kepala_keluarga=False,
            status_keluarga="ISTRI",
            status_tinggal="TETAP",
        )

        client = Client()
        client.login(username=self.test_user, password=self.test_pass)

        # Test Daftar Kepala Keluarga page
        response = client.get(reverse("kependudukan:daftarKepalaKeluarga"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Kepala Keluarga Test")
        self.assertNotContains(response, "Anggota Test")

        # Test AJAX endpoint
        ajax_url = reverse(
            "kependudukan:detailAnggotaKeluarga",
            kwargs={"idkompleks": self.existing_kompleks.id},
        )
        response_ajax = client.get(ajax_url)
        self.assertEqual(response_ajax.status_code, 200)
        self.assertContains(response_ajax, "Kepala Keluarga Test")
        self.assertContains(response_ajax, "Anggota Test")
        self.assertContains(response_ajax, "Istri")

    def test_csv_import_status_keluarga(self):
        from django.core.files.uploadedfile import SimpleUploadedFile

        # Prepare CSV data
        csv_content = (
            "nama_lengkap,nik,no_kk,no_hp,pekerjaan,agama,status_kawin,tanggal_lahir,tempat_lahir,jenis_kelamin,status_tinggal,alamat_ktp,status_keluarga\n"
            "Imported Suami,nik-import-1,kk-import,081,SWASTA,islam,KAWIN,1990-01-01,Jakarta,Laki-laki,TETAP,-,SUAMI\n"
            "Imported Istri,nik-import-2,kk-import,081,SWASTA,islam,KAWIN,1992-01-01,Jakarta,Perempuan,TETAP,-, ISTRI \n"  # with space
            "Imported Child,nik-import-3,kk-import,081,SWASTA,islam,BELUM KAWIN,2015-01-01,Jakarta,Perempuan,TETAP,-,INVALID_VALUE\n"  # invalid
        )
        csv_file = SimpleUploadedFile(
            "test_warga.csv", csv_content.encode("utf-8"), content_type="text/csv"
        )

        client = Client()
        client.login(username=self.test_user, password=self.test_pass)

        response = client.post(
            reverse("kependudukan:utilImportWarga"),
            {"csv_file": csv_file, "submit": "1"},
        )
        if response.status_code != 302:
            print("CSV Import Failure Content:", response.content.decode("utf-8"))
        self.assertEqual(response.status_code, 302)

        # Verify database records
        suami = Warga.objects.get(nik="nik-import-1")
        self.assertEqual(suami.status_keluarga, "SUAMI")

        istri = Warga.objects.get(nik="nik-import-2")
        self.assertEqual(istri.status_keluarga, "ISTRI")  # verify trimming works!

        child = Warga.objects.get(nik="nik-import-3")
        self.assertEqual(
            child.status_keluarga, "N/A"
        )  # verify invalid value falls back to N/A

    def test_warga_list_search_by_no_kk(self):
        # Create user permission so user can list
        from ..models import UserPermission, WargaPermissionGroup

        group = WargaPermissionGroup.objects.create(group_name="all")
        UserPermission.objects.create(user=self.user, permission_group=group)

        # Create Warga with specific KK number
        Warga.objects.create(
            nama_lengkap="Special KK Member",
            nik="nik_special_kk",
            no_kk="9876543210123456",
            kompleks=self.existing_kompleks,
            status_tinggal="TETAP",
            agama="ISLAM",
            jenis_kelamin="LAKI-LAKI",
        )

        client = Client()
        client.login(username=self.test_user, password=self.test_pass)

        # 1. Search by partial KK (wildcard) on main list view
        response = client.get(
            reverse("kependudukan:listWargaView"), {"search": "76543210"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Special KK Member")

        # 2. Search by partial KK (wildcard) on API search view
        import json

        token_response = client.post(
            reverse("kependudukan:token_obtain_pair"),
            data=json.dumps({"username": self.test_user, "password": self.test_pass}),
            content_type="application/json",
        )
        self.assertEqual(token_response.status_code, 200)
        token = token_response.json()["access"]

        response_api = client.post(
            reverse("kependudukan:warga-search"),
            data=json.dumps({"search": "76543210"}),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response_api.status_code, 200)
        self.assertContains(response_api, "Special KK Member")

    def test_warga_list_context_defaults(self):
        # Create user permission so user can list
        from ..models import UserPermission, WargaPermissionGroup

        group = WargaPermissionGroup.objects.create(group_name="all")
        UserPermission.objects.create(user=self.user, permission_group=group)

        client = Client()
        client.login(username=self.test_user, password=self.test_pass)

        # GET request without cluster query param should default to "all"
        response = client.get(reverse("kependudukan:listWargaView"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["cluster"], "all")

        # GET request for Kepala Keluarga list without cluster query param should also default to "all"
        response_kk = client.get(reverse("kependudukan:daftarKepalaKeluarga"))
        self.assertEqual(response_kk.status_code, 200)
        self.assertEqual(response_kk.context["cluster"], "all")

    def test_detail_warga_logged(self):
        from ..models import UserPermission, WargaPermissionGroup
        group = WargaPermissionGroup.objects.create(group_name="all")
        UserPermission.objects.create(user=self.user, permission_group=group)

        client = Client()
        client.login(username=self.test_user, password=self.test_pass)
        
        detail_url = reverse("kependudukan:detailWarga", kwargs={"idwarga": self.existing_warga.id})
        response = client.get(detail_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.test_nama_lengkap)
        self.assertTemplateUsed(response, "detail_warga.html")

    def test_detail_warga_unlogged(self):
        client = Client()
        detail_url = reverse("kependudukan:detailWarga", kwargs={"idwarga": self.existing_warga.id})
        response = client.get(detail_url)
        self.assertEqual(response.status_code, 302)

    def test_detail_warga_notfound(self):
        from ..models import UserPermission, WargaPermissionGroup
        group, _ = WargaPermissionGroup.objects.get_or_create(group_name="all")
        UserPermission.objects.get_or_create(user=self.user, permission_group=group)

        client = Client()
        client.login(username=self.test_user, password=self.test_pass)
        
        detail_url = reverse("kependudukan:detailWarga", kwargs={"idwarga": 99999})
        response = client.get(detail_url)
        self.assertEqual(response.status_code, 404)

    def test_detail_warga_pdf_logged(self):
        from ..models import UserPermission, WargaPermissionGroup
        group, _ = WargaPermissionGroup.objects.get_or_create(group_name="all")
        UserPermission.objects.get_or_create(user=self.user, permission_group=group)

        client = Client()
        client.login(username=self.test_user, password=self.test_pass)
        
        pdf_url = reverse("kependudukan:pdfDetailWarga", kwargs={"idwarga": self.existing_warga.id})
        response = client.get(pdf_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertIn("inline; filename=", response["Content-Disposition"])

    def test_detail_warga_pdf_unlogged(self):
        client = Client()
        pdf_url = reverse("kependudukan:pdfDetailWarga", kwargs={"idwarga": self.existing_warga.id})
        response = client.get(pdf_url)
        self.assertEqual(response.status_code, 302)

    def test_detail_warga_pdf_notfound(self):
        from ..models import UserPermission, WargaPermissionGroup
        group, _ = WargaPermissionGroup.objects.get_or_create(group_name="all")
        UserPermission.objects.get_or_create(user=self.user, permission_group=group)

        client = Client()
        client.login(username=self.test_user, password=self.test_pass)
        
        pdf_url = reverse("kependudukan:pdfDetailWarga", kwargs={"idwarga": 99999})
        response = client.get(pdf_url)
        self.assertEqual(response.status_code, 404)
