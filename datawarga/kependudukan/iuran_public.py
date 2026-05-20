from .models import Kompleks, TransaksiIuranBulanan
from .utility import helper_finance_year_list
from django.shortcuts import render
import logging

logger = logging.getLogger(__name__)


def form_iuran_bulanan_display(request):
    list_kompleks = Kompleks.objects.order_by("id")
    context = {"list_kompleks": list_kompleks}
    context["iuran_year_period"] = helper_finance_year_list()

    if request.POST:
        id_komplek = int(request.POST["kompleks"])
        periode_tahun = str(request.POST["periode_tahun"])
        list_trx = TransaksiIuranBulanan.objects.order_by("periode_bulan").filter(
            periode_tahun=periode_tahun, kompleks__id=id_komplek
        )
        data_kompleks = Kompleks.objects.get(pk=id_komplek)
        context["data_pembayaran"] = list_trx
        context["periode_tahun"] = periode_tahun
        context["data_kompleks"] = data_kompleks

    return render(request=request, template_name="public/iuran.html", context=context)
