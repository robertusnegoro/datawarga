from __future__ import annotations
from django.core.management import call_command
from django.test import TestCase
from kependudukan.models import (
    Warga,
    Kompleks,
    TransaksiIuranBulanan,
    SummaryTransaksiBulanan,
)


class GenerateDummyDataTestCase(TestCase):

    def test_default_generation(self) -> None:
        """Test standard execution with 10 complexes and 100% occupancy."""
        # Execute the command
        call_command(
            "generate_dummy_data", total_kompleks=10, occupancy_rate=1.0, years=1
        )

        # Check complexes count
        self.assertEqual(Kompleks.objects.count(), 10)

        # Check residents exist
        warga_qs = Warga.objects.all()
        self.assertGreater(warga_qs.count(), 0)

        # For each kompleks, check familial constraints:
        # 1. Exactly one kepala_keluarga = True
        # 2. All family members share the same no_kk
        for kompleks in Kompleks.objects.all():
            family = Warga.objects.filter(kompleks=kompleks)
            self.assertGreater(family.count(), 0)

            heads = family.filter(kepala_keluarga=True)
            self.assertEqual(heads.count(), 1)

            kk_set = {member.no_kk for member in family}
            self.assertEqual(len(kk_set), 1)

        # Verify NIKs are all unique
        niks = [w.nik for w in warga_qs]
        self.assertEqual(len(niks), len(set(niks)))

        # Verify transactions and summaries were created
        self.assertGreater(TransaksiIuranBulanan.objects.count(), 0)
        self.assertGreater(SummaryTransaksiBulanan.objects.count(), 0)

    def test_clear_data(self) -> None:
        """Test that passing --clear deletes existing data first."""
        # Pre-populate
        k = Kompleks.objects.create(blok="Z", nomor="99")
        Warga.objects.create(
            nama_lengkap="Old Warga", nik="1111222233334444", kompleks=k
        )

        # Run command with clear
        call_command("generate_dummy_data", total_kompleks=5, clear=True, years=1)

        # Verify old data is gone
        self.assertFalse(Warga.objects.filter(nama_lengkap="Old Warga").exists())
        self.assertEqual(Kompleks.objects.count(), 5)

    def test_unoccupied_houses(self) -> None:
        """Test execution with 0% occupancy rate."""
        call_command("generate_dummy_data", total_kompleks=5, occupancy_rate=0.0)

        # Complexes should be generated, but no warga or payments
        self.assertEqual(Kompleks.objects.count(), 5)
        self.assertEqual(Warga.objects.count(), 0)
        self.assertEqual(TransaksiIuranBulanan.objects.count(), 0)

        # Summaries are created by the shared summarize logic, but all months should be False
        self.assertEqual(SummaryTransaksiBulanan.objects.count(), 10)
        for s in SummaryTransaksiBulanan.objects.all():
            self.assertFalse(s.january)
            self.assertFalse(s.february)
            self.assertFalse(s.march)
            self.assertFalse(s.april)
            self.assertFalse(s.may)
            self.assertFalse(s.june)
            self.assertFalse(s.july)
            self.assertFalse(s.august)
            self.assertFalse(s.september)
            self.assertFalse(s.october)
            self.assertFalse(s.november)
            self.assertFalse(s.december)
