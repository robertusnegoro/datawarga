from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.test import APITestCase

from kependudukan.models import (
    Warga,
    Kompleks,
    TransaksiIuranBulanan,
    WargaUpdateRequest,
    Surat,
    Kendaraan,
    Penandatangan,
    KasTransaksi,
)


class AdminAPIEndpointsTestCase(APITestCase):
    def setUp(self):
        # 1. Create standard structures
        self.kompleks_a = Kompleks.objects.create(
            alamat="Jl. Melati 1",
            cluster="Melati",
            blok="M1",
            nomor="10",
            rt="01",
            rw="02",
        )
        self.kompleks_b = Kompleks.objects.create(
            alamat="Jl. Melati 2",
            cluster="Melati",
            blok="M1",
            nomor="11",
            rt="01",
            rw="02",
        )

        # 2. Create users and associate Warga
        # Admin / Staff user (no warga profile, has staff role)
        self.admin_user = User.objects.create_user(
            username="admin_staff_api", password="password123", is_staff=True
        )

        # Citizen User A
        self.citizen_user_a = User.objects.create_user(
            username="citizen_a", password="password123"
        )
        self.warga_a = Warga.objects.create(
            nama_lengkap="Warga A",
            nik="1111111111111112",
            agama="ISLAM",
            jenis_kelamin="LAKI-LAKI",
            kompleks=self.kompleks_a,
            user=self.citizen_user_a,
        )

        # Citizen User B
        self.citizen_user_b = User.objects.create_user(
            username="citizen_b", password="password123"
        )
        self.warga_b = Warga.objects.create(
            nama_lengkap="Warga B",
            nik="2222222222222223",
            agama="KRISTEN",
            jenis_kelamin="PEREMPUAN",
            kompleks=self.kompleks_b,
            user=self.citizen_user_b,
        )

        # Penandatangan (Signee)
        self.penandatangan = Penandatangan.objects.create(
            nama="Pak RT A", jabatan="Ketua RT 01", aktif=True
        )

        # 3. Create dummy entities for processing
        # Iuran pending
        self.iuran_pending = TransaksiIuranBulanan.objects.create(
            kompleks=self.kompleks_a,
            periode_bulan=1,
            periode_tahun=2026,
            total_bayar=100000,
            status="PENDING",
        )

        # Warga update request pending
        self.update_req_pending = WargaUpdateRequest.objects.create(
            warga=self.warga_a,
            requested_by=self.warga_a,
            kompleks=self.kompleks_a,
            is_new_warga=False,
            data_changes={"nama_lengkap": "Warga A Updated"},
            status="PENDING",
        )

        # Surat pending
        self.surat_pending = Surat.objects.create(
            warga=self.warga_a,
            jenis_surat="PENGANTAR_RT",
            keperluan="Mengurus KTP",
            status="PENDING",
        )

        # Kendaraan pending
        self.kendaraan_pending = Kendaraan.objects.create(
            pemilik=self.warga_a,
            jenis_kendaraan="MOBIL",
            plat_nomor="B1234ABC",
            status="PENDING",
        )

    def test_anonymous_user_access_blocked(self):
        """Verify anonymous users are rejected with 401 Unauthorized for admin APIs."""
        self.client.force_authenticate(user=None)

        endpoints = [
            ("/api/admin/warga-updates/", "get"),
            (f"/api/admin/warga-updates/{self.update_req_pending.id}/approve/", "post"),
            (f"/api/admin/warga-updates/{self.update_req_pending.id}/reject/", "post"),
            ("/api/admin/surat/", "get"),
            (f"/api/admin/surat/{self.surat_pending.id}/approve/", "post"),
            (f"/api/admin/surat/{self.surat_pending.id}/reject/", "post"),
            ("/api/admin/kendaraan/", "get"),
            (f"/api/admin/kendaraan/{self.kendaraan_pending.id}/approve/", "post"),
            (f"/api/admin/kendaraan/{self.kendaraan_pending.id}/reject/", "post"),
            ("/api/admin/penandatangan/", "get"),
            (f"/api/iuran/{self.iuran_pending.id}/approve/", "post"),
            (f"/api/iuran/{self.iuran_pending.id}/reject/", "post"),
        ]

        for path, method in endpoints:
            if method == "get":
                response = self.client.get(path)
            else:
                response = self.client.post(path, data={"reason": "Test Reject"})
            self.assertEqual(
                response.status_code,
                status.HTTP_401_UNAUTHORIZED,
                f"Path {path} did not return 401",
            )

    def test_citizen_user_access_blocked(self):
        """Verify citizens are rejected with 403 Forbidden for admin APIs."""
        self.client.force_authenticate(user=self.citizen_user_a)

        endpoints = [
            ("/api/admin/warga-updates/", "get"),
            (f"/api/admin/warga-updates/{self.update_req_pending.id}/approve/", "post"),
            (f"/api/admin/warga-updates/{self.update_req_pending.id}/reject/", "post"),
            ("/api/admin/surat/", "get"),
            (f"/api/admin/surat/{self.surat_pending.id}/approve/", "post"),
            (f"/api/admin/surat/{self.surat_pending.id}/reject/", "post"),
            ("/api/admin/kendaraan/", "get"),
            (f"/api/admin/kendaraan/{self.kendaraan_pending.id}/approve/", "post"),
            (f"/api/admin/kendaraan/{self.kendaraan_pending.id}/reject/", "post"),
            ("/api/admin/penandatangan/", "get"),
            (f"/api/iuran/{self.iuran_pending.id}/approve/", "post"),
            (f"/api/iuran/{self.iuran_pending.id}/reject/", "post"),
        ]

        for path, method in endpoints:
            if method == "get":
                response = self.client.get(path)
            else:
                response = self.client.post(path, data={"reason": "Test Reject"})
            self.assertEqual(
                response.status_code,
                status.HTTP_403_FORBIDDEN,
                f"Path {path} did not return 403",
            )

    def test_warga_me_update_limits_to_same_rumah(self):
        """Verify warga can only update their own or family member (same kompleks) data."""
        self.client.force_authenticate(user=self.citizen_user_a)

        # 1. Update own profile: should succeed
        response = self.client.post(
            "/api/warga/me/update/",
            {"nama_lengkap": "My New Name", "pekerjaan": "PNS"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # 2. Update Warga B (in different kompleks): should return 400 Bad Request
        response = self.client.post(
            "/api/warga/me/update/",
            {
                "target_warga_id": self.warga_b.id,
                "nama_lengkap": "Warga B Modified Name",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.json()["error"],
            "Target warga tidak valid atau tidak berada dalam satu rumah.",
        )

        # 3. Create family member in same house (Kompleks A)
        family_member = Warga.objects.create(
            nama_lengkap="Family Member of A",
            nik="3333333333333334",
            agama="ISLAM",
            jenis_kelamin="PEREMPUAN",
            kompleks=self.kompleks_a,
        )
        response = self.client.post(
            "/api/warga/me/update/",
            {
                "target_warga_id": family_member.id,
                "nama_lengkap": "Family Member Name Updated",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_admin_approve_and_reject_iuran(self):
        """Verify admin can approve/reject iuran requests."""
        self.client.force_authenticate(user=self.admin_user)

        # 1. Approve iuran
        response = self.client.post(f"/api/iuran/{self.iuran_pending.id}/approve/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.iuran_pending.refresh_from_db()
        self.assertEqual(self.iuran_pending.status, "APPROVED")
        self.assertTrue(
            KasTransaksi.objects.filter(iuran_asal=self.iuran_pending).exists()
        )

        # 2. Reject iuran (needs reason)
        iuran_reject = TransaksiIuranBulanan.objects.create(
            kompleks=self.kompleks_b,
            periode_bulan=2,
            periode_tahun=2026,
            total_bayar=100000,
            status="PENDING",
        )
        response = self.client.post(f"/api/iuran/{iuran_reject.id}/reject/")
        self.assertEqual(
            response.status_code, status.HTTP_400_BAD_REQUEST
        )  # No reason provided

        response = self.client.post(
            f"/api/iuran/{iuran_reject.id}/reject/",
            {"reason": "Bukti transfer tidak jelas"},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        iuran_reject.refresh_from_db()
        self.assertEqual(iuran_reject.status, "REJECTED")
        self.assertIn("Bukti transfer tidak jelas", iuran_reject.keterangan_status)

    def test_admin_approve_and_reject_warga_updates(self):
        """Verify admin can list, approve, and reject warga update requests."""
        self.client.force_authenticate(user=self.admin_user)

        # 1. List
        response = self.client.get("/api/admin/warga-updates/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.json()["results"]), 1)

        # 2. Approve update request
        response = self.client.post(
            f"/api/admin/warga-updates/{self.update_req_pending.id}/approve/"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.update_req_pending.refresh_from_db()
        self.assertEqual(self.update_req_pending.status, "APPROVED")
        self.warga_a.refresh_from_db()
        self.assertEqual(self.warga_a.nama_lengkap, "Warga A Updated")

        # 3. Reject update request
        update_req_reject = WargaUpdateRequest.objects.create(
            warga=self.warga_b,
            requested_by=self.warga_b,
            kompleks=self.kompleks_b,
            is_new_warga=False,
            data_changes={"nama_lengkap": "Warga B Spam"},
            status="PENDING",
        )
        response = self.client.post(
            f"/api/admin/warga-updates/{update_req_reject.id}/reject/"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)  # No reason

        response = self.client.post(
            f"/api/admin/warga-updates/{update_req_reject.id}/reject/",
            {"reason": "Data tidak valid"},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        update_req_reject.refresh_from_db()
        self.assertEqual(update_req_reject.status, "REJECTED")
        self.assertIn("Data tidak valid", update_req_reject.notes)

    def test_admin_approve_and_reject_surat(self):
        """Verify admin can list, approve, and reject document (surat) requests."""
        self.client.force_authenticate(user=self.admin_user)

        # 1. List
        response = self.client.get("/api/admin/surat/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # 2. Approve surat (supports nomor_surat and penandatangan ID)
        data = {
            "nomor_surat": "123/RT/2026",
            "penandatangan": self.penandatangan.id,
        }
        response = self.client.post(
            f"/api/admin/surat/{self.surat_pending.id}/approve/", data=data
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.surat_pending.refresh_from_db()
        self.assertEqual(self.surat_pending.status, "APPROVED")
        self.assertEqual(self.surat_pending.nomor_surat, "123/RT/2026")
        self.assertEqual(self.surat_pending.penandatangan, self.penandatangan)

        # 3. Reject surat
        surat_reject = Surat.objects.create(
            warga=self.warga_b,
            jenis_surat="KETERANGAN_DOMISILI",
            keperluan="Bekerja",
            status="PENDING",
        )
        response = self.client.post(f"/api/admin/surat/{surat_reject.id}/reject/")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)  # No reason

        response = self.client.post(
            f"/api/admin/surat/{surat_reject.id}/reject/", {"reason": "Kurang lampiran"}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        surat_reject.refresh_from_db()
        self.assertEqual(surat_reject.status, "REJECTED")
        self.assertIn("Kurang lampiran", surat_reject.keterangan_status)

    def test_admin_approve_and_reject_kendaraan(self):
        """Verify admin can list, approve, and reject vehicle (kendaraan) registrations."""
        self.client.force_authenticate(user=self.admin_user)

        # 1. List
        response = self.client.get("/api/admin/kendaraan/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # 2. Approve kendaraan
        response = self.client.post(
            f"/api/admin/kendaraan/{self.kendaraan_pending.id}/approve/"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.kendaraan_pending.refresh_from_db()
        self.assertEqual(self.kendaraan_pending.status, "APPROVED")

        # 3. Reject kendaraan
        kendaraan_reject = Kendaraan.objects.create(
            pemilik=self.warga_b,
            jenis_kendaraan="MOTOR",
            plat_nomor="D9876XYZ",
            status="PENDING",
        )
        response = self.client.post(
            f"/api/admin/kendaraan/{kendaraan_reject.id}/reject/"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)  # No reason

        response = self.client.post(
            f"/api/admin/kendaraan/{kendaraan_reject.id}/reject/",
            {"reason": "Bukan penghuni"},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        kendaraan_reject.refresh_from_db()
        self.assertEqual(kendaraan_reject.status, "REJECTED")
        self.assertIn("Bukan penghuni", kendaraan_reject.keterangan_status)

    def test_admin_penandatangan_crud(self):
        """Verify admin can perform CRUD on Penandatangan."""
        self.client.force_authenticate(user=self.admin_user)

        # 1. List
        response = self.client.get("/api/admin/penandatangan/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.json()["results"]), 1)

        # 2. Create
        data = {
            "nama": "Pak RT B",
            "jabatan": "Ketua RT 02",
            "aktif": True,
        }
        response = self.client.post("/api/admin/penandatangan/", data=data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Penandatangan.objects.filter(nama="Pak RT B").exists())

        # 3. Update
        created_pt = Penandatangan.objects.get(nama="Pak RT B")
        response = self.client.put(
            f"/api/admin/penandatangan/{created_pt.id}/",
            {
                "nama": "Pak RT B Updated",
                "jabatan": "Ketua RT 02 Baru",
                "aktif": False,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        created_pt.refresh_from_db()
        self.assertEqual(created_pt.nama, "Pak RT B Updated")
        self.assertFalse(created_pt.aktif)

        # 4. Delete
        response = self.client.delete(f"/api/admin/penandatangan/{created_pt.id}/")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Penandatangan.objects.filter(nama="Pak RT B Updated").exists())

    def test_admin_endpoint_status_filtering(self):
        """Verify status query parameter filters responses correctly."""
        self.client.force_authenticate(user=self.admin_user)

        # Create approved counterparts for filtering check
        TransaksiIuranBulanan.objects.create(
            kompleks=self.kompleks_a,
            periode_bulan=2,
            periode_tahun=2026,
            total_bayar=100000,
            status="APPROVED",
        )
        WargaUpdateRequest.objects.create(
            warga=self.warga_b,
            requested_by=self.warga_b,
            kompleks=self.kompleks_b,
            is_new_warga=False,
            data_changes={"nama_lengkap": "Approved Update"},
            status="APPROVED",
        )
        Surat.objects.create(
            warga=self.warga_b,
            jenis_surat="KETERANGAN_DOMISILI",
            keperluan="Approved Surat",
            status="APPROVED",
        )
        Kendaraan.objects.create(
            pemilik=self.warga_b,
            jenis_kendaraan="MOTOR",
            plat_nomor="D5555OK",
            status="APPROVED",
        )

        filter_test_cases = [
            ("/api/admin/warga-updates/", 1),
            ("/api/admin/surat/", 1),
            ("/api/admin/kendaraan/", 1),
            ("/api/iuran/", 1),
        ]

        for path, expected_pending_count in filter_test_cases:
            # Test filtering status=PENDING
            response = self.client.get(path, {"status": "PENDING"})
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            results = response.json()["results"]
            self.assertEqual(
                len(results),
                expected_pending_count,
                f"Pending count check failed for {path}",
            )
            for item in results:
                self.assertEqual(item["status"], "PENDING")

            # Test filtering status=APPROVED
            response_approved = self.client.get(path, {"status": "APPROVED"})
            self.assertEqual(response_approved.status_code, status.HTTP_200_OK)
            results_approved = response_approved.json()["results"]
            self.assertEqual(
                len(results_approved),
                1,
                f"Approved count check failed for {path}",
            )
            for item in results_approved:
                self.assertEqual(item["status"], "APPROVED")

    def test_admin_dashboard_endpoint(self):
        """Verify AdminDashboardViewSet returns correct aggregation, counts, and lists of pending entities."""
        # 1. Access checks
        # Anonymous
        self.client.force_authenticate(user=None)
        response_anon = self.client.get("/api/admin/dashboard/")
        self.assertEqual(response_anon.status_code, status.HTTP_401_UNAUTHORIZED)

        # Citizen (Warga)
        self.client.force_authenticate(user=self.citizen_user_a)
        response_citizen = self.client.get("/api/admin/dashboard/")
        self.assertEqual(response_citizen.status_code, status.HTTP_403_FORBIDDEN)

        # Admin (Staff)
        self.client.force_authenticate(user=self.admin_user)

        # Create additional test data:
        # 1. An approved iuran payment for the current year (should be counted)
        from django.utils import timezone

        current_year = timezone.now().year
        TransaksiIuranBulanan.objects.create(
            kompleks=self.kompleks_a,
            periode_bulan=3,
            periode_tahun=current_year,
            total_bayar=150000,
            status="APPROVED",
        )
        # 2. A pending iuran payment for the current year (should NOT be counted in total_iuran but in pending_counts)
        TransaksiIuranBulanan.objects.create(
            kompleks=self.kompleks_b,
            periode_bulan=4,
            periode_tahun=current_year,
            total_bayar=200000,
            status="PENDING",
        )

        response = self.client.get("/api/admin/dashboard/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()

        # Verify summary totals — must be DB-level counts, not page-limited results.
        # setUp creates 2 Warga (warga_a, warga_b) and 2 Kompleks (kompleks_a, kompleks_b).
        self.assertEqual(data["total_warga"], 2)
        self.assertEqual(data["total_rumah"], 2)

        # Verify total iuran current year (only APPROVED, not PENDING)
        # We had:
        # self.iuran_pending (status=PENDING, current year 2026, total_bayar=100000) -> not counted
        # new approved (total_bayar=150000) -> counted
        # new pending (total_bayar=200000) -> not counted
        # So it should be 150000.
        self.assertEqual(data["total_iuran_current_year"], 150000)

        # Verify pending counts
        # We have iuran pending: self.iuran_pending, and new pending iuran -> total 2.
        # Warga updates: self.update_req_pending -> total 1.
        # Surat: self.surat_pending -> total 1.
        # Kendaraan: self.kendaraan_pending -> total 1.
        self.assertEqual(data["pending_counts"]["iuran"], 2)
        self.assertEqual(data["pending_counts"]["warga_updates"], 1)
        self.assertEqual(data["pending_counts"]["surat"], 1)
        self.assertEqual(data["pending_counts"]["kendaraan"], 1)

        # Verify pending lists structure and contents
        self.assertEqual(len(data["pending_list"]["iuran"]), 2)
        self.assertEqual(len(data["pending_list"]["warga_updates"]), 1)
        self.assertEqual(len(data["pending_list"]["surat"]), 1)
        self.assertEqual(len(data["pending_list"]["kendaraan"]), 1)

        # Verify details of a serialized object
        self.assertEqual(data["pending_list"]["surat"][0]["keperluan"], "Mengurus KTP")
        self.assertEqual(data["pending_list"]["kendaraan"][0]["plat_nomor"], "B1234ABC")

    def test_warga_api_create_with_nested_kompleks(self):
        """Verify admin can create warga with nested kompleks object."""
        self.client.force_authenticate(user=self.admin_user)

        payload = {
            "nama_lengkap": "New Warga API",
            "nik": "1234567890123456",
            "agama": "ISLAM",
            "jenis_kelamin": "LAKI-LAKI",
            "kompleks": {"id": self.kompleks_a.id},
        }
        response = self.client.post("/api/warga/", data=payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Verify created in DB
        warga = Warga.objects.get(nik="1234567890123456")
        self.assertEqual(warga.nama_lengkap, "New Warga API")
        self.assertEqual(warga.kompleks, self.kompleks_a)

    def test_warga_api_update_with_nested_kompleks(self):
        """Verify admin can update warga complexes and fields with nested kompleks object."""
        self.client.force_authenticate(user=self.admin_user)

        payload = {
            "nama_lengkap": "Warga A Updated via API",
            "kompleks": {"id": self.kompleks_b.id},
        }
        response = self.client.patch(
            f"/api/warga/{self.warga_a.id}/", data=payload, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.warga_a.refresh_from_db()
        self.assertEqual(self.warga_a.nama_lengkap, "Warga A Updated via API")
        self.assertEqual(self.warga_a.kompleks, self.kompleks_b)
