from .forms import IuranBulananForm
from .models import Warga, Kompleks, TransaksiIuranBulanan
from .utility import helper_finance_year_list
from datetime import datetime
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, Http404, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.core import serializers
from urllib.parse import urlencode
import logging
import json

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
    ).filter(periode_tahun=year, kompleks__id=idkompleks)

    if "message" in request.GET:
        context["message"] = str(request.GET["message"])

    return render(
        request=request, template_name="form_iuran_bulanan.html", context=context
    )


@login_required
def form_iuran_bulanan_save(request):
    if request.POST:
        form = IuranBulananForm(request.POST, request.FILES)

        check_existing_trx = TransaksiIuranBulanan.objects.filter(
            periode_bulan=str(request.POST["periode_bulan"]),
            periode_tahun=str(request.POST["periode_tahun"]),
            kompleks__id=int(request.POST["kompleks"]),
        )

        if len(check_existing_trx) > 0:
            error_message = "Iuran pada Bulan %s Tahun %s sudah dibayar" % (
                str(request.POST["periode_bulan"]),
                str(request.POST["periode_tahun"]),
            )
            logger.error(error_message)
            return HttpResponse(error_message)

        if form.is_valid():
            if "idtransaksi" in request.POST:
                idtransaksi = int(request.POST["idtransaksi"])
                data_transaksi = get_object_or_404(
                    TransaksiIuranBulanan, pk=idtransaksi
                )
                form = IuranBulananForm(
                    request.POST, request.FILES, instance=data_transaksi
                )

            iuran = form.save()

            base_url = reverse(
                "kependudukan:detailKompleks",
                kwargs={"idkompleks": int(request.POST["kompleks"])},
            )
            payload = urlencode({"message": "iuran bulanan is saved!"})
            url_redir = "{}?{}".format(base_url, payload)
            return redirect(url_redir)
        else:
            logger.info(form.errors)
            return HttpResponse("form is not valid %s" % (form.errors))
    else:
        return Http404()


@login_required
def list_iuran_kompleks_tahun_json(
    request, idkompleks, year=datetime.now().strftime("%Y")
):
    list_trx = TransaksiIuranBulanan.objects.order_by("periode_bulan").filter(
        periode_tahun=year, kompleks__id=idkompleks
    )
    total_trx = len(list_trx)
    data = serializers.serialize("json", list_trx)
    response = {"data": json.loads(data), "total": total_trx}
    return JsonResponse(response)


@login_required
def delete_iuran_bulanan(request, idtransaksi):
    data_transaksi = get_object_or_404(TransaksiIuranBulanan, pk=idtransaksi)
    kompleks_id = data_transaksi.kompleks.id
    if request.POST:
        data_transaksi.delete()
        logger.info("Deleting data transaksi with id : %s" % (idtransaksi))
        base_url = reverse(
            "kependudukan:detailKompleks",
            kwargs={"idkompleks": kompleks_id},
        )
        payload = urlencode({"message": "data %s was deleted!" % (idtransaksi)})
        url_redir = "{}?{}".format(base_url, payload)
        return redirect(url_redir)

    context = {"data": data_transaksi}

    return render(
        request, template_name="delete_form_iuran_bulanan.html", context=context
    )
