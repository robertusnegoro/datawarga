from datetime import date, timedelta
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from kependudukan.models import (
    Kompleks,
    WargaPermissionGroup,
    UserPermission,
    KasTransaksi,
    KasTagihan,
    TransaksiIuranBulanan,
)


class KasTestCase(TestCase):
    def setUp(self):
        # Create test users
        self.super_user = User.objects.create_superuser(
            username="admin", email="admin@example.com", password="adminpassword"
        )
        self.normal_user = User.objects.create_user(
            username="warga1", password="wargapassword"
        )
        self.bendahara_user = User.objects.create_user(
            username="bendahara1", password="bendaharapassword"
        )

        # Assign bendahara to permission group
        self.group_bendahara = WargaPermissionGroup.objects.create(
            group_name="bendahara"
        )
        UserPermission.objects.create(
            user=self.bendahara_user, permission_group=self.group_bendahara
        )

        # Create a Kompleks for Iuran testing
        self.kompleks = Kompleks.objects.create(
            alamat="Jl. Melati No. 10",
            cluster="Cluster Melati",
            blok="M1",
            nomor="10",
            rt="001",
            rw="002",
        )

    def test_kas_access_control(self):
        """
        Tests that only authorized users (superuser, bendahara/rt_pic group) can access Kas views,
        while normal users and anonymous users are blocked (fails closed).
        """
        urls = [
            reverse("kependudukan:dashboard_kas"),
            reverse("kependudukan:list_kas_transaksi"),
            reverse("kependudukan:form_kas_transaksi"),
            reverse("kependudukan:list_kas_tagihan"),
            reverse("kependudukan:form_kas_tagihan"),
            reverse("kependudukan:sync_iuran_to_kas"),
            reverse("kependudukan:pdf_report_kas"),
            reverse("kependudukan:laporan_kas"),
        ]

        # 1. Anonymous User
        anon_client = Client()
        for url in urls:
            response = anon_client.get(url)
            # Should redirect to login
            self.assertEqual(response.status_code, 302)

        # 2. Normal Warga (Authenticated but no permissions)
        normal_client = Client()
        normal_client.login(username="warga1", password="wargapassword")
        for url in urls:
            response = normal_client.get(url)
            self.assertEqual(response.status_code, 403)

        # 3. Bendahara User (Authenticated with bendahara group name)
        bendahara_client = Client()
        bendahara_client.login(username="bendahara1", password="bendaharapassword")
        for url in urls:
            response = bendahara_client.get(url)
            if url == reverse("kependudukan:sync_iuran_to_kas"):
                self.assertEqual(response.status_code, 302)
            else:
                self.assertEqual(response.status_code, 200)

        # 4. Superuser (Authenticated)
        admin_client = Client()
        admin_client.login(username="admin", password="adminpassword")
        for url in urls:
            response = admin_client.get(url)
            if url == reverse("kependudukan:sync_iuran_to_kas"):
                self.assertEqual(response.status_code, 302)
            else:
                self.assertEqual(response.status_code, 200)

    def test_iuran_signals_propagation(self):
        """
        Verifies that saving, updating, and deleting TransaksiIuranBulanan
        automatically creates, updates, and deletes corresponding KasTransaksi ledger entries.
        """
        # Save a new iuran transaction
        iuran = TransaksiIuranBulanan.objects.create(
            kompleks=self.kompleks,
            periode_bulan=5,
            periode_tahun=2026,
            total_bayar=150000,
            keterangan="Iuran bulanan May 2026",
        )

        # Check corresponding KasTransaksi created
        kas_tx = KasTransaksi.objects.filter(iuran_asal=iuran).first()
        self.assertIsNotNone(kas_tx)
        self.assertEqual(kas_tx.jenis, "PEMASUKAN")
        self.assertEqual(kas_tx.kategori, "IURAN")
        self.assertEqual(kas_tx.jumlah, 150000)

        # Update iuran amount
        iuran.total_bayar = 175000
        iuran.save()

        # Check KasTransaksi updated
        kas_tx.refresh_from_db()
        self.assertEqual(kas_tx.jumlah, 175000)

        # Delete iuran
        iuran_id = iuran.id
        iuran.delete()

        # Check KasTransaksi deleted
        self.assertFalse(KasTransaksi.objects.filter(iuran_asal_id=iuran_id).exists())

    def test_tagihan_settlement_workflow(self):
        """
        Verifies that settling (paying) a bill:
        1. Marks the bill status as LUNAS.
        2. Automatically creates a corresponding ledger record.
        """
        # Create a Piutang (receivable) bill
        piutang = KasTagihan.objects.create(
            judul="Tagihan Donasi 17an",
            jenis="PIUTANG",
            kategori="DONASI",
            jumlah=100000,
            tanggal_jatuh_tempo=date.today() + timedelta(days=5),
            status="BELUM",
            keterangan="Iuran donasi Agustusan",
        )

        client = Client()
        client.login(username="bendahara1", password="bendaharapassword")

        # Pay/settle the bill
        response = client.get(
            reverse("kependudukan:bayar_tagihan", kwargs={"idtagihan": piutang.id})
        )
        self.assertEqual(response.status_code, 302)  # Should redirect back to list

        # Assert status updated to LUNAS
        piutang.refresh_from_db()
        self.assertEqual(piutang.status, "LUNAS")

        # Assert automated KasTransaksi created
        kas_tx = KasTransaksi.objects.filter(tagihan_asal=piutang).first()
        self.assertIsNotNone(kas_tx)
        self.assertEqual(kas_tx.jenis, "PEMASUKAN")
        self.assertEqual(kas_tx.kategori, "DONASI")
        self.assertEqual(kas_tx.jumlah, 100000)
        self.assertIn("Pelunasan tagihan: Tagihan Donasi 17an", kas_tx.keterangan)

    def test_sync_iuran_to_kas(self):
        """
        Verifies batch synchronization to import existing TransaksiIuranBulanan
        payments into KasTransaksi ledger.
        """
        # Delete any signal-created KasTransaksi first to simulate historical desynced data
        KasTransaksi.objects.all().delete()

        # Create two iurans without triggering signals updates in KasTransaksi (by temporarily disconnecting signals, or just creating iurans and then deleting kas records)
        iuran1 = TransaksiIuranBulanan.objects.create(
            kompleks=self.kompleks,
            periode_bulan=1,
            periode_tahun=2026,
            total_bayar=100000,
        )
        iuran2 = TransaksiIuranBulanan.objects.create(
            kompleks=self.kompleks,
            periode_bulan=2,
            periode_tahun=2026,
            total_bayar=100000,
        )

        # Clear signal-created kas records to simulate manual/batch sync requirement
        KasTransaksi.objects.all().delete()
        self.assertEqual(KasTransaksi.objects.count(), 0)

        # Run synchronization
        client = Client()
        client.login(username="bendahara1", password="bendaharapassword")
        response = client.get(reverse("kependudukan:sync_iuran_to_kas"))
        self.assertEqual(response.status_code, 302)

        # Verify kas entries are generated
        self.assertEqual(KasTransaksi.objects.count(), 2)
        self.assertTrue(KasTransaksi.objects.filter(iuran_asal=iuran1).exists())
        self.assertTrue(KasTransaksi.objects.filter(iuran_asal=iuran2).exists())

    def test_pdf_report_generation(self):
        """
        Verifies that calling the pdf report view returns a valid PDF attachment.
        """
        # Create some dummy transactions
        KasTransaksi.objects.create(
            tanggal=date.today(),
            jenis="PEMASUKAN",
            kategori="IURAN",
            jumlah=50000,
            keterangan="Iuran Warga",
        )
        KasTransaksi.objects.create(
            tanggal=date.today(),
            jenis="PENGELUARAN",
            kategori="OPERASIONAL",
            jumlah=20000,
            keterangan="Beli ATK",
        )

        client = Client()
        client.login(username="bendahara1", password="bendaharapassword")

        # Download report
        response = client.get(reverse("kependudukan:pdf_report_kas"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertTrue(response.has_header("Content-Disposition"))
        self.assertIn("attachment", response["Content-Disposition"])
        self.assertIn("laporan_keuangan_kas_rt", response["Content-Disposition"])

    def test_laporan_cutoff_and_filters(self):
        """
        Tests the cutoff calculations and filters for the laporan_kas and pdf_report_kas views:
        1. Correctly calculates Saldo Awal (transactions before start_date).
        2. Correctly filters transactions within the range.
        3. Correctly calculates Saldo Akhir (initial + net change).
        """
        # Delete existing signal-created or setUp transactions
        KasTransaksi.objects.all().delete()

        # Create transactions
        # T1 (pemasukan, 100,000, 2026-05-01)
        KasTransaksi.objects.create(
            tanggal=date(2026, 5, 1),
            jenis="PEMASUKAN",
            kategori="IURAN",
            jumlah=100000,
            keterangan="Transaksi 1",
        )
        # T2 (pengeluaran, 20,000, 2026-05-05)
        KasTransaksi.objects.create(
            tanggal=date(2026, 5, 5),
            jenis="PENGELUARAN",
            kategori="OPERASIONAL",
            jumlah=20000,
            keterangan="Transaksi 2",
        )
        # T3 (pemasukan, 50,000, 2026-05-15)
        KasTransaksi.objects.create(
            tanggal=date(2026, 5, 15),
            jenis="PEMASUKAN",
            kategori="IURAN",
            jumlah=50000,
            keterangan="Transaksi 3",
        )
        # T4 (pengeluaran, 10,000, 2026-05-20)
        KasTransaksi.objects.create(
            tanggal=date(2026, 5, 20),
            jenis="PENGELUARAN",
            kategori="OPERASIONAL",
            jumlah=10000,
            keterangan="Transaksi 4",
        )
        # T5 (pemasukan, 200,000, 2026-06-01)
        KasTransaksi.objects.create(
            tanggal=date(2026, 6, 1),
            jenis="PEMASUKAN",
            kategori="IURAN",
            jumlah=200000,
            keterangan="Transaksi 5",
        )

        client = Client()
        client.login(username="bendahara1", password="bendaharapassword")

        # Test filter date range: 2026-05-10 to 2026-05-25
        response = client.get(
            reverse("kependudukan:laporan_kas"),
            {"start_date": "2026-05-10", "end_date": "2026-05-25"},
        )
        self.assertEqual(response.status_code, 200)

        # Retrieve context values
        context = response.context
        self.assertEqual(context["saldo_awal"], 80000)  # T1 - T2 = 100,000 - 20,000
        self.assertEqual(context["total_pemasukan"], 50000)  # T3 = 50,000
        self.assertEqual(context["total_pengeluaran"], 10000)  # T4 = 10,000
        self.assertEqual(context["saldo_akhir"], 120000)  # 80k + 50k - 10k

        # Verify queryset contains exactly T3 and T4
        tx_list = list(context["transaksi_list"])
        self.assertEqual(len(tx_list), 2)
        self.assertEqual(tx_list[0].keterangan, "Transaksi 3")
        self.assertEqual(tx_list[1].keterangan, "Transaksi 4")

    def test_laporan_default_current_month_and_pagination(self):
        """
        Verifies that accessing reports with no URL parameters defaults
        to the current month, and limits the transaction list preview to 20 entries (pagination).
        """
        # Delete existing transactions
        KasTransaksi.objects.all().delete()

        # Create 25 transactions in the current month
        today = date.today()
        for i in range(25):
            KasTransaksi.objects.create(
                tanggal=today,
                jenis="PEMASUKAN",
                kategori="IURAN",
                jumlah=10000,
                keterangan=f"Transaksi default {i}",
            )

        client = Client()
        client.login(username="bendahara1", password="bendaharapassword")

        # Request report page with absolutely no parameters
        response = client.get(reverse("kependudukan:laporan_kas"))
        self.assertEqual(response.status_code, 200)

        context = response.context
        # Check that start_date and end_date default to the current month
        expected_start = today.replace(day=1).strftime("%Y-%m-%d")
        import calendar

        last_day = calendar.monthrange(today.year, today.month)[1]
        expected_end = today.replace(day=last_day).strftime("%Y-%m-%d")

        self.assertEqual(context["selected_start_date"], expected_start)
        self.assertEqual(context["selected_end_date"], expected_end)

        # Check pagination (limit 20 entries)
        tx_list = list(context["transaksi_list"])
        self.assertEqual(len(tx_list), 20)  # Only 20 items on the first page
        self.assertEqual(context["page_obj"].paginator.count, 25)  # Total 25 entries
