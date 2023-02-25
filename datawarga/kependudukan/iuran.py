from .forms import IuranBulananForm
from .models import Warga, Kompleks, TransaksiIuranBulanan
from .utility import helper_finance_year_list
from datetime import datetime
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, Http404, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from urllib.parse import urlencode
import logging

logger = logging.getLogger(__name__)


@login_required
def form_iuran_bulanan(
    request, idkompleks, year=datetime.now().strftime("%Y"), idtransaksi=0
):
    data_kompleks = get_object_or_404(Kompleks, pk=idkompleks)
    context = {}
    context["data_kompleks"] = data_kompleks
    context["year"] = year
    context["month"] = TransaksiIuranBulanan.LIST_BULAN
    context["iuran_year_period"] = helper_finance_year_list()
    context["form"] = IuranBulananForm()
    context["default_iuran_amount"] = settings.IURAN_BULANAN

    if idtransaksi > 0:
        iuran_record = get_object_or_404(TransaksiIuranBulanan, pk=idtransaksi)
        context["iuran_record"] = iuran_record
        context["form"] = IuranBulananForm(instance=iuran_record)
        context["year"] = iuran_record.periode_tahun

    context["data_iuran"] = TransaksiIuranBulanan.objects.order_by(
        "periode_bulan"
    ).filter(periode_tahun=year)

    return render(
        request=request, template_name="form_iuran_bulanan.html", context=context
    )


@login_required
def form_iuran_bulanan_save(request):
    if request.POST:
        form = IuranBulananForm(request.POST, request.FILES)

        

        if form.is_valid():
            if "idtransaksi" in request.POST:
                idtransaksi = int(request.POST["idtransaksi"])
                data_transaksi = get_object_or_404(TransaksiIuranBulanan, pk=idtransaksi)
                form = IuranBulananForm(request.POST, request.FILES, instance=data_transaksi)
            else:
                check_existing_trx = TransaksiIuranBulanan.objects.filter(periode_bulan=str(request.POST["periode_bulan"]), periode_tahun=str(request.POST["periode_tahun"]))
                if len(check_existing_trx) > 0:
                    error_message = "Iuran pada Bulan %s Tahun %s sudah dibayar" % (str(request.POST["periode_bulan"]), str(request.POST["periode_tahun"]))
                    logger.error(error_message)
                    return HttpResponse(error_message)

            iuran = form.save()

            base_url = reverse(
                "kependudukan:formIuranBulananYear",
                kwargs={
                    "idkompleks": int(request.POST["kompleks"]),
                    "year": int(request.POST["periode_tahun"]),
                },
            )
            payload = urlencode({"message": "data saved!"})
            url_redir = "{}?{}".format(base_url, payload)
            return redirect(url_redir)
        else:
            logger.info(form.errors)
            return HttpResponse("form is not valid %s" % (form.errors))
    else:
        return Http404()
