from kependudukan.models import Warga, Kompleks, TransaksiIuranBulanan, SummaryTransaksiBulanan
from django.core.management import BaseCommand
from datetime import datetime

def summarize(year, blok):
    print("Summarizing period : %s, Blok : %s" % (year, blok))
    blok = blok.upper()
    list_kompleks = Kompleks.objects.filter(blok=blok)
    for rumah in list_kompleks:
        print(rumah)
        iuran = TransaksiIuranBulanan.objects.filter(kompleks=rumah.id, periode_tahun=year)
        summary_data = create_if_not_exists(year, rumah)
        for bayar in iuran:
            print(bayar.periode_bulan)
            update_summary = summary_data.update_month_field(bayar.periode_bulan, True)

        print('--------------------')


def create_if_not_exists(year, rumah):
    try:
        get_data = SummaryTransaksiBulanan.objects.get(periode_tahun=year, kompleks=rumah)
        return get_data
    except SummaryTransaksiBulanan.DoesNotExist:
        summary_data = SummaryTransaksiBulanan(periode_tahun=year, kompleks=rumah)
        summary_data.save()
        return summary_data

class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument("--blok", required=True, type=str)
        parser.add_argument("--year", required=False, type=int, default=datetime.now().year)

    def handle(self, *args, **options):
        kompleks = summarize(options["year"], options["blok"])