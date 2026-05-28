import io
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework.test import APITestCase
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image

from kependudukan.models import (
    Warga,
    Kompleks,
    Surat,
    TransaksiIuranBulanan,
    Kendaraan,
    WargaUpdateRequest,
    KasTransaksi,
    Penandatangan,
    UserInvitation,
)


class WargaPortalTestCase(TestCase):
    def setUp(self):
        # Create administrative staff user
        self.staff_user = User.objects.create_user(
            username="admin_staff", password="password123", is_staff=True
        )

        # Create penandatangan (signee) for document approval
        self.penandatangan = Penandatangan.objects.create(
            nama="Budi RT", jabatan="Ketua RT 01", aktif=True
        )

        # Create complexes
        self.kompleks_a = Kompleks.objects.create(
            alamat="Jl. Tulip", blok="A", nomor="10", rt="01", rw="02"
        )
        self.kompleks_b = Kompleks.objects.create(
            alamat="Jl. Tulip", blok="A", nomor="11", rt="01", rw="02"
        )

        # Create residents (warga)
        self.warga_a = Warga.objects.create(
            nama_lengkap="Warga Tulip 10",
            nik="1111111111111111",
            agama="ISLAM",
            jenis_kelamin="LAKI-LAKI",
            kompleks=self.kompleks_a,
        )
        self.warga_b = Warga.objects.create(
            nama_lengkap="Warga Tulip 11",
            nik="2222222222222222",
            agama="KRISTEN",
            jenis_kelamin="PEREMPUAN",
            kompleks=self.kompleks_b,
        )

    def test_admin_preserved_flows(self):
        """
        Verify that admin-driven creation bypasses the pending status
        and immediately sets status to APPROVED.
        """
        # Admin creates a letter directly
        surat = Surat.objects.create(
            warga=self.warga_a,
            jenis_surat="SPRT",
            keperluan="Administrasi langsung oleh admin",
        )
        self.assertEqual(surat.status, "APPROVED")

        # Admin creates a vehicle directly
        kendaraan = Kendaraan.objects.create(
            pemilik=self.warga_a,
            jenis_kendaraan="MOBIL",
            plat_nomor="B1234XYZ",
        )
        self.assertEqual(kendaraan.status, "APPROVED")

        # Admin records an iuran payment
        iuran = TransaksiIuranBulanan.objects.create(
            kompleks=self.kompleks_a,
            periode_bulan=5,
            periode_tahun=2026,
            total_bayar=100000,
        )
        self.assertEqual(iuran.status, "APPROVED")
        # Check that it automatically synced to KasTransaksi due to APPROVED status
        kas_exists = KasTransaksi.objects.filter(iuran_asal=iuran).exists()
        self.assertTrue(kas_exists)

    def test_authorization_guard_enforcement(self):
        """
        Verify that citizen (warga) users are blocked from backoffice views.
        """
        # Create citizen user
        citizen_user = User.objects.create_user(
            username="citizen_user", password="password123"
        )
        self.warga_a.user = citizen_user
        self.warga_a.save()

        # Login as citizen
        self.client.login(username="citizen_user", password="password123")

        # Citizen attempts to access backoffice list view
        response = self.client.get(reverse("kependudukan:listWargaView"))
        self.assertEqual(response.status_code, 403)

        # Citizen attempts to view detail of another citizen
        response = self.client.get(
            reverse("kependudukan:detailWarga", kwargs={"idwarga": self.warga_b.id})
        )
        self.assertEqual(response.status_code, 403)

        # Citizen attempts to view the admin approvals dashboard
        response = self.client.get(reverse("kependudukan:admin_approvals"))
        self.assertEqual(response.status_code, 403)

    def test_invitation_and_activation_flow(self):
        """
        Verify the process of inviting a resident, activating their user account, and logging in.
        """
        # Admin logs in
        self.client.login(username="admin_staff", password="password123")

        # Post invitation request
        response = self.client.post(
            reverse(
                "kependudukan:warga_invite_login", kwargs={"idwarga": self.warga_b.id}
            ),
            {"email": "warga_b@email.com"},
        )
        self.assertEqual(response.status_code, 302)  # Redirects back to detail page

        # Retrieve invitation record
        invitation = UserInvitation.objects.get(user__username="warga_b@email.com")
        self.assertFalse(invitation.is_used)
        self.assertFalse(invitation.user.is_active)
        self.assertEqual(invitation.user.warga, self.warga_b)

        # Logout admin
        self.client.logout()

        # Public activation page loading
        act_url = reverse(
            "kependudukan:user_activate", kwargs={"token": invitation.token}
        )
        response = self.client.get(act_url)
        self.assertEqual(response.status_code, 200)

        # Post password to activate
        response = self.client.post(
            act_url,
            {"new_password1": "newpassword123", "new_password2": "newpassword123"},
        )
        self.assertEqual(response.status_code, 302)  # Redirects to login

        # Verify user is active
        invitation.refresh_from_db()
        self.assertTrue(invitation.is_used)
        self.assertTrue(invitation.user.is_active)

        # Citizen log in and access citizen dashboard
        login_success = self.client.login(
            username="warga_b@email.com", password="newpassword123"
        )
        self.assertTrue(login_success)

        response = self.client.get(reverse("kependudukan:warga_dashboard"))
        self.assertEqual(response.status_code, 200)

    def test_citizen_requests_and_approvals_flow(self):
        """
        Verify citizen profile update requests, surat, iuran, and vehicle submissions
        followed by admin approval/rejections.
        """
        # Setup citizen user
        citizen_user = User.objects.create_user(
            username="citizen_user", password="password123"
        )
        self.warga_a.user = citizen_user
        self.warga_a.save()

        # Login as citizen
        self.client.login(username="citizen_user", password="password123")

        # 1. Profile Update Submission
        response = self.client.post(
            reverse("kependudukan:warga_submit_update"),
            {
                "nama_lengkap": " Tulip Ten Updated",
                "agama": "KATHOLIK",
                "no_hp": "089999999",
            },
        )
        self.assertEqual(response.status_code, 302)  # Redirects back
        # Verify Warga original model remains unchanged
        self.warga_a.refresh_from_db()
        self.assertEqual(self.warga_a.nama_lengkap, "Warga Tulip 10")
        # Verify update request exists
        update_req = WargaUpdateRequest.objects.get(warga=self.warga_a)
        self.assertEqual(update_req.status, "PENDING")
        self.assertEqual(update_req.data_changes["nama_lengkap"], "Tulip Ten Updated")

        # 2. Document Request Submission
        response = self.client.post(
            reverse("kependudukan:warga_request_surat"),
            {"jenis_surat": "SKD", "keperluan": "Membuka rekening bank"},
        )
        self.assertEqual(response.status_code, 302)
        surat = Surat.objects.get(warga=self.warga_a)
        self.assertEqual(surat.status, "PENDING")

        # 3. Vehicle Registration Submission
        response = self.client.post(
            reverse("kependudukan:warga_register_kendaraan"),
            {
                "jenis_kendaraan": "MOTOR",
                "plat_nomor": "D4321ABC",
                "merk": "Honda",
                "tipe": "Vario",
            },
        )
        self.assertEqual(response.status_code, 302)
        kendaraan = Kendaraan.objects.get(pemilik=self.warga_a)
        self.assertEqual(kendaraan.status, "PENDING")

        # 4. Dues Payment Upload Submission
        # Generate dummy image bytes for upload
        im = Image.new("RGB", (50, 50), (255, 0, 0))
        im_io = io.BytesIO()
        im.save(im_io, "JPEG")
        bukti_file = SimpleUploadedFile(
            "bukti.jpg", im_io.getvalue(), content_type="image/jpeg"
        )

        response = self.client.post(
            reverse("kependudukan:warga_upload_iuran"),
            {
                "periode_bulan": 6,
                "periode_tahun": 2026,
                "total_bayar": 100000,
                "bukti_bayar": bukti_file,
                "keterangan": "Iuran bulan Juni",
            },
        )
        self.assertEqual(response.status_code, 302)
        iuran = TransaksiIuranBulanan.objects.get(
            kompleks=self.kompleks_a, status="PENDING"
        )
        self.assertFalse(KasTransaksi.objects.filter(iuran_asal=iuran).exists())

        # Citizen Logout
        self.client.logout()

        # Admin logs in to process approvals
        self.client.login(username="admin_staff", password="password123")

        # Approve Profile Update
        response = self.client.post(
            reverse("kependudukan:admin_approvals"),
            {"action": "approve_warga", "id": update_req.id},
        )
        self.assertEqual(response.status_code, 302)
        # Verify original Warga model is now updated
        self.warga_a.refresh_from_db()
        self.assertEqual(self.warga_a.nama_lengkap, "Tulip Ten Updated")
        self.assertEqual(self.warga_a.agama, "KATHOLIK")
        update_req.refresh_from_db()
        self.assertEqual(update_req.status, "APPROVED")

        # Approve Surat Request (with nomor & signee)
        response = self.client.post(
            reverse("kependudukan:admin_approvals"),
            {
                "action": "approve_surat",
                "id": surat.id,
                "nomor_surat": "001/SKD/RT01/2026",
                "penandatangan": self.penandatangan.id,
            },
        )
        self.assertEqual(response.status_code, 302)
        surat.refresh_from_db()
        self.assertEqual(surat.status, "APPROVED")
        self.assertEqual(surat.nomor_surat, "001/SKD/RT01/2026")
        self.assertEqual(surat.penandatangan, self.penandatangan)

        # Reject Vehicle Registration with reason
        response = self.client.post(
            reverse("kependudukan:admin_approvals"),
            {
                "action": "reject_kendaraan",
                "id": kendaraan.id,
                "reason": "Format plat nomor tidak valid",
            },
        )
        self.assertEqual(response.status_code, 302)
        kendaraan.refresh_from_db()
        self.assertEqual(kendaraan.status, "REJECTED")
        self.assertIn("Format plat nomor tidak valid", kendaraan.keterangan_status)

        # Approve Iuran payment
        response = self.client.post(
            reverse("kependudukan:admin_approvals"),
            {"action": "approve_iuran", "id": iuran.id},
        )
        self.assertEqual(response.status_code, 302)
        iuran.refresh_from_db()
        self.assertEqual(iuran.status, "APPROVED")
        # Verify it successfully synced to KasTransaksi
        self.assertTrue(KasTransaksi.objects.filter(iuran_asal=iuran).exists())

    @override_settings(IURAN_BULANAN=275000)
    def test_warga_dashboard_dues_default_amount(self):
        """
        Verify that citizen dashboard context contains the correct iuran_bulanan setting.
        """
        citizen_user = User.objects.create_user(
            username="citizen_test", password="password123"
        )
        self.warga_a.user = citizen_user
        self.warga_a.save()

        self.client.login(username="citizen_test", password="password123")
        response = self.client.get(reverse("kependudukan:warga_dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["iuran_bulanan"], 275000)

    @override_settings(IURAN_BULANAN=315000)
    def test_warga_upload_iuran_defaults_to_setting(self):
        """
        Verify that uploading iuran proof without total_bayar defaults to settings.IURAN_BULANAN.
        """
        citizen_user = User.objects.create_user(
            username="citizen_test", password="password123"
        )
        self.warga_a.user = citizen_user
        self.warga_a.save()

        self.client.login(username="citizen_test", password="password123")

        im = Image.new("RGB", (50, 50), (255, 0, 0))
        im_io = io.BytesIO()
        im.save(im_io, "JPEG")
        bukti_file = SimpleUploadedFile(
            "bukti_default.jpg", im_io.getvalue(), content_type="image/jpeg"
        )

        response = self.client.post(
            reverse("kependudukan:warga_upload_iuran"),
            {
                "periode_bulan": 7,
                "periode_tahun": 2026,
                # total_bayar is omitted to test default value
                "bukti_bayar": bukti_file,
                "keterangan": "Default iuran test",
            },
        )
        self.assertEqual(response.status_code, 302)
        iuran = TransaksiIuranBulanan.objects.get(
            kompleks=self.kompleks_a, periode_bulan=7, periode_tahun=2026
        )
        self.assertEqual(iuran.total_bayar, 315000)


class WargaAPIEndpointsTestCase(APITestCase):
    def setUp(self):
        # Create citizen user and administrative staff
        self.citizen_user = User.objects.create_user(
            username="citizen_api", password="password123"
        )
        self.kompleks = Kompleks.objects.create(
            alamat="Jl. Tulip", blok="A", nomor="10", rt="01", rw="02"
        )
        self.warga = Warga.objects.create(
            nama_lengkap="Warga API",
            nik="9999999999999999",
            agama="ISLAM",
            jenis_kelamin="LAKI-LAKI",
            kompleks=self.kompleks,
            user=self.citizen_user,  # Link citizen user
        )
        self.client.force_authenticate(user=self.citizen_user)

    def test_warga_me_endpoint(self):
        """
        Verify GET /api/warga/me/ endpoint returns correct citizen record.
        """
        response = self.client.get("/api/warga/me/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["nik"], "9999999999999999")
        self.assertEqual(data["nama_lengkap"], "Warga API")

    def test_warga_me_update_endpoint(self):
        """
        Verify POST /api/warga/me/update/ creates a WargaUpdateRequest.
        """
        response = self.client.post(
            "/api/warga/me/update/",
            {"nama_lengkap": "New API Name", "pekerjaan": "PNS"},
            format="json",
        )
        self.assertEqual(response.status_code, 201)

        # Verify request created in DB
        update_req = WargaUpdateRequest.objects.get(warga=self.warga)
        self.assertEqual(update_req.status, "PENDING")
        self.assertEqual(update_req.data_changes["nama_lengkap"], "New API Name")

    def test_warga_me_surat_endpoint(self):
        """
        Verify GET & POST for /api/warga/me/surat/ endpoints.
        """
        # POST a document request
        response = self.client.post(
            "/api/warga/me/surat/",
            {"jenis_surat": "SPRT", "keperluan": "Surat pengantar nikah"},
            format="json",
        )
        self.assertEqual(response.status_code, 201)

        # GET document requests list
        response = self.client.get("/api/warga/me/surat/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["keperluan"], "Surat pengantar nikah")
        self.assertEqual(data[0]["status"], "PENDING")

    def test_warga_me_blocked_from_general_endpoint(self):
        """
        Verify that citizen users cannot access the general administrative list endpoints.
        """
        response = self.client.get("/api/warga/")
        self.assertEqual(response.status_code, 403)

    def test_warga_me_update_family_member(self):
        """
        Verify that citizen can submit update request for a family member in the same complex.
        """
        family_member = Warga.objects.create(
            nama_lengkap="Family Member",
            nik="8888888888888888",
            agama="ISLAM",
            jenis_kelamin="PEREMPUAN",
            kompleks=self.kompleks,
        )
        response = self.client.post(
            "/api/warga/me/update/",
            {
                "target_warga_id": family_member.id,
                "nama_lengkap": "Family Member Updated",
                "pekerjaan": "KARYAWAN",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)

        # Verify request created in DB
        update_req = WargaUpdateRequest.objects.get(warga=family_member)
        self.assertEqual(update_req.status, "PENDING")
        self.assertEqual(
            update_req.data_changes["nama_lengkap"], "Family Member Updated"
        )
        self.assertEqual(update_req.requested_by, self.warga)

    def test_warga_me_update_new_family_member(self):
        """
        Verify that citizen can submit update request for a new family member (NEW).
        """
        response = self.client.post(
            "/api/warga/me/update/",
            {
                "target_warga_id": "NEW",
                "nama_lengkap": "New Born Baby",
                "pekerjaan": "BELUM/TIDAK BEKERJA",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)

        # Verify request created in DB
        update_req = WargaUpdateRequest.objects.get(warga=None, is_new_warga=True)
        self.assertEqual(update_req.status, "PENDING")
        self.assertEqual(update_req.data_changes["nama_lengkap"], "New Born Baby")
        self.assertEqual(update_req.kompleks, self.kompleks)
        self.assertEqual(update_req.requested_by, self.warga)

    def test_warga_me_update_other_house_blocked(self):
        """
        Verify that citizen cannot update data of a resident in a different complex.
        """
        other_kompleks = Kompleks.objects.create(
            alamat="Jl. Tulip", blok="B", nomor="20", rt="01", rw="02"
        )
        other_warga = Warga.objects.create(
            nama_lengkap="Other Resident",
            nik="7777777777777777",
            agama="KRISTEN",
            jenis_kelamin="LAKI-LAKI",
            kompleks=other_kompleks,
        )
        response = self.client.post(
            "/api/warga/me/update/",
            {
                "target_warga_id": other_warga.id,
                "nama_lengkap": "Malicious Update",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.json())
        self.assertEqual(
            response.json()["error"],
            "Target warga tidak valid atau tidak berada dalam satu rumah.",
        )

        # Verify no request is created in DB for other_warga
        self.assertFalse(WargaUpdateRequest.objects.filter(warga=other_warga).exists())

    def test_warga_me_iuran_own_complex(self):
        """
        Verify that citizen can submit dues payment proof for their own complex.
        """
        im = Image.new("RGB", (50, 50), (255, 0, 0))
        im_io = io.BytesIO()
        im.save(im_io, "JPEG")
        bukti_file = SimpleUploadedFile(
            "bukti.jpg", im_io.getvalue(), content_type="image/jpeg"
        )

        response = self.client.post(
            "/api/warga/me/iuran/",
            {
                "periode_bulan": 8,
                "periode_tahun": 2026,
                "total_bayar": 100000,
                "bukti_bayar": bukti_file,
                "keterangan": "Iuran Agustus",
            },
            format="multipart",
        )
        self.assertEqual(response.status_code, 201)

        # Verify created in DB and associated with user's complex
        iuran = TransaksiIuranBulanan.objects.get(
            kompleks=self.kompleks, periode_bulan=8, periode_tahun=2026
        )
        self.assertEqual(iuran.status, "PENDING")
        self.assertEqual(iuran.total_bayar, 100000)

    def test_warga_me_iuran_always_uses_own_complex(self):
        """
        Verify that citizen submitting dues payment cannot target another complex.
        Even if they try to pass metadata/fields, the system always uses their own complex.
        """
        other_kompleks = Kompleks.objects.create(
            alamat="Jl. Tulip", blok="B", nomor="20", rt="01", rw="02"
        )
        im = Image.new("RGB", (50, 50), (255, 0, 0))
        im_io = io.BytesIO()
        im.save(im_io, "JPEG")
        bukti_file = SimpleUploadedFile(
            "bukti.jpg", im_io.getvalue(), content_type="image/jpeg"
        )

        response = self.client.post(
            "/api/warga/me/iuran/",
            {
                "kompleks": other_kompleks.id,  # Attempt to target other complex
                "periode_bulan": 9,
                "periode_tahun": 2026,
                "total_bayar": 100000,
                "bukti_bayar": bukti_file,
                "keterangan": "Attempt other complex",
            },
            format="multipart",
        )
        self.assertEqual(response.status_code, 201)

        # Verify the created transaction is for own complex, NOT other_kompleks
        self.assertFalse(
            TransaksiIuranBulanan.objects.filter(
                kompleks=other_kompleks, periode_bulan=9, periode_tahun=2026
            ).exists()
        )
        self.assertTrue(
            TransaksiIuranBulanan.objects.filter(
                kompleks=self.kompleks, periode_bulan=9, periode_tahun=2026
            ).exists()
        )
