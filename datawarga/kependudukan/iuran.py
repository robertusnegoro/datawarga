from .forms import IuranBulananForm
from .models import Warga, Kompleks, TransaksiIuranBulanan, SummaryTransaksiBulanan
from .utility import helper_finance_year_list
from datetime import datetime
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core import serializers
from django.db.models import Count, Sum
from django.http import HttpResponse, Http404, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.template.loader import render_to_string
from django.urls import reverse
from urllib.parse import urlencode
from weasyprint import HTML
from weasyprint.text.fonts import FontConfiguration
import json
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
    ).filter(periode_tahun=year, kompleks__id=idkompleks)

    if "message" in request.GET:
        context["message"] = str(request.GET["message"])

    return render(
        request=request, template_name="form_iuran_bulanan.html", context=context
    )


def check_existing_trx_bulan(bulan, tahun, kompleks):
    check_existing_trx = TransaksiIuranBulanan.objects.filter(
        periode_bulan=str(bulan),
        periode_tahun=str(tahun),
        kompleks__id=int(kompleks),
    )
    if len(check_existing_trx) > 0:
        return False
    else:
        return True


@login_required
def form_iuran_bulanan_save(request):
    if request.POST:
        form = IuranBulananForm(request.POST, request.FILES)

        if form.is_valid():
            if "idtransaksi" in request.POST:
                idtransaksi = int(request.POST["idtransaksi"])
                data_transaksi = get_object_or_404(
                    TransaksiIuranBulanan, pk=idtransaksi
                )

                if int(data_transaksi.periode_bulan) != int(
                    request.POST["periode_bulan"]
                ):
                    test_check = check_existing_trx_bulan(
                        request.POST["periode_bulan"],
                        request.POST["periode_tahun"],
                        request.POST["kompleks"],
                    )
                    if not test_check:
                        error_message = "Iuran pada Bulan %s Tahun %s sudah dibayar" % (
                            int(request.POST["periode_bulan"]),
                            str(request.POST["periode_tahun"]),
                        )
                        logger.error(error_message)
                        return HttpResponse(error_message)

                form = IuranBulananForm(
                    request.POST, request.FILES, instance=data_transaksi
                )
            else:
                test_check = check_existing_trx_bulan(
                    request.POST["periode_bulan"],
                    request.POST["periode_tahun"],
                    request.POST["kompleks"],
                )
                if not test_check:
                    error_message = "Iuran pada Bulan %s Tahun %s sudah dibayar" % (
                        int(request.POST["periode_bulan"]),
                        str(request.POST["periode_tahun"]),
                    )
                    logger.error(error_message)
                    return HttpResponse(error_message)

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


@login_required
def pdfReportIuranBulananForm(request):
    get_year = (
        (
            SummaryTransaksiBulanan.objects.all()
            .values("periode_tahun")
            .annotate(count=Count("periode_tahun"))
        )
        .order_by("-year")[:10]
        .values_list("year", flat=True)
    )
    context = {"years": get_year}
    return render(
        request, template_name="form_summary_iuran_bulanan.html", context=context
    )


@login_required
def pdf_report_iuranbulanan(request, year):
    data_iuran_summary = SummaryTransaksiBulanan.objects.filter(
        periode_tahun=year
    ).order_by("kompleks")
    report_data = {"data": data_iuran_summary, "year": year}
    report_data["rw"] = settings.RUKUNWARGA
    report_data["alamat"] = settings.ALAMAT
    report_data["kelurahan"] = settings.KELURAHAN
    report_data["kecamatan"] = settings.KECAMATAN
    report_data["kota"] = settings.KOTA
    report_data["provinsi"] = settings.PROVINSI
    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = "inline; filename=summary-iuranbulanan.pdf"
    html = render_to_string("summary-iuranbulanan-pdf.html", report_data)
    font_config = FontConfiguration()
    HTML(string=html).write_pdf(response, font_config=font_config)
    return response


@login_required
def iuranIncomeStatementReportForm(request):
    context = {}
    current_year = int(datetime.now().strftime("%Y"))
    context["range_tahun"] = [
        year for year in range(current_year, current_year - 6, -1)
    ]
    context["range_bulan"] = TransaksiIuranBulanan.indonesian_months
    return render(
        request, template_name="form_iuran_income_statement.html", context=context
    )


@login_required
def iuranIncomeStatementReportFormExec(request):
    context = {}
    if request.POST:
        year = int(request.POST["periode_tahun"])
        month = str(request.POST["periode_bulan"])
        month_number = TransaksiIuranBulanan.indonesian_months.index(month) + 1
        transaction = TransaksiIuranBulanan.objects.filter(
            tanggal_bayar__month=month_number, tanggal_bayar__year=year
        )
        context["transaction"] = transaction
        context["total_sum"] = transaction.aggregate(Sum("total_bayar"))
        context["year"] = year
        context["month"] = month
        return render(
            request,
            template_name="form_iuran_income_statement_exec.html",
            context=context,
        )
