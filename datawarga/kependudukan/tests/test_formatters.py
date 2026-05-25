from django.test import SimpleTestCase
from ..utils.formatters import format_rupiah


class FormattersTestCase(SimpleTestCase):
    def test_format_rupiah_positive(self):
        self.assertEqual(format_rupiah(150000), "Rp 150.000")
        self.assertEqual(format_rupiah(5000), "Rp 5.000")
        self.assertEqual(format_rupiah(1250350), "Rp 1.250.350")

    def test_format_rupiah_negative(self):
        self.assertEqual(format_rupiah(-50000), "- Rp 50.000")
        self.assertEqual(format_rupiah(-1250000), "- Rp 1.250.000")

    def test_format_rupiah_none(self):
        self.assertEqual(format_rupiah(None), "Rp 0")

    def test_format_rupiah_zero(self):
        self.assertEqual(format_rupiah(0), "Rp 0")

    def test_format_rupiah_string_number(self):
        self.assertEqual(format_rupiah("150000"), "Rp 150.000")
        self.assertEqual(format_rupiah("-75000"), "- Rp 75.000")

    def test_format_rupiah_invalid_value(self):
        self.assertEqual(format_rupiah("not_a_number"), "not_a_number")
