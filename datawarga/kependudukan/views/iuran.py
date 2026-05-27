from kependudukan.forms import IuranBulananForm, BatchIuranBulananForm
from kependudukan.models import Kompleks, TransaksiIuranBulanan, SummaryTransaksiBulanan
from kependudukan.views.utility import helper_finance_year_list
from datetime import datetime
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core import serializers
from django.db.models import Count, Sum
from django.db.models.functions import TruncMonth
from django.http import HttpResponse, Http404, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.template.loader import render_to_string
from django.urls import reverse
from weasyprint import HTML
from weasyprint.text.fonts import FontConfiguration
import json
import logging
from kependudukan.utils.auth_guards import admin_or_petugas_required

logger = logging.getLogger(__name__)


@login_required
@admin_or_petugas_required
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
@admin_or_petugas_required
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
                        bulan_num = int(request.POST["periode_bulan"])
                        tahun_str = str(request.POST["periode_tahun"])
                        bulan_name = dict(TransaksiIuranBulanan.LIST_BULAN).get(
                            bulan_num, bulan_num
                        )
                        error_message = f"Iuran pada bulan <strong>{bulan_name} {tahun_str}</strong> sudah tercatat."
                        logger.error(
                            "Duplicate iuran attempt: bulan %s tahun %s"
                            % (bulan_num, tahun_str)
                        )
                        messages.error(request, error_message)
                        kompleks_id = int(request.POST["kompleks"])
                        return redirect(
                            reverse(
                                "kependudukan:formIuranBulananYearTrx",
                                kwargs={
                                    "idkompleks": kompleks_id,
                                    "year": int(tahun_str),
                                    "idtransaksi": idtransaksi,
                                },
                            )
                        )

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
                    bulan_num = int(request.POST["periode_bulan"])
                    tahun_str = str(request.POST["periode_tahun"])
                    bulan_name = dict(TransaksiIuranBulanan.LIST_BULAN).get(
                        bulan_num, bulan_num
                    )
                    error_message = f"Iuran pada bulan <strong>{bulan_name} {tahun_str}</strong> sudah tercatat."
                    logger.error(
                        "Duplicate iuran attempt: bulan %s tahun %s"
                        % (bulan_num, tahun_str)
                    )
                    messages.error(request, error_message)
                    kompleks_id = int(request.POST["kompleks"])
                    return redirect(
                        reverse(
                            "kependudukan:formIuranBulananYear",
                            kwargs={"idkompleks": kompleks_id, "year": int(tahun_str)},
                        )
                    )

            form.save()

            kompleks_id = int(request.POST["kompleks"])
            messages.success(request, "Iuran bulanan berhasil disimpan.")
            return redirect(
                reverse(
                    "kependudukan:detailKompleks",
                    kwargs={"idkompleks": kompleks_id},
                )
            )
        else:
            logger.info(form.errors)
            return HttpResponse("form is not valid %s" % (form.errors))
    else:
        return Http404()


@login_required
@admin_or_petugas_required
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
@admin_or_petugas_required
def delete_iuran_bulanan(request, idtransaksi):
    data_transaksi = get_object_or_404(TransaksiIuranBulanan, pk=idtransaksi)
    kompleks_id = data_transaksi.kompleks.id
    if request.POST:
        bulan_display = dict(TransaksiIuranBulanan.LIST_BULAN).get(
            data_transaksi.periode_bulan, data_transaksi.periode_bulan
        )
        tahun_display = data_transaksi.periode_tahun
        data_transaksi.delete()
        logger.info("Deleting data transaksi with id : %s" % (idtransaksi))
        messages.success(
            request,
            f"Iuran bulanan untuk bulan <strong>{bulan_display} {tahun_display}</strong> berhasil dihapus.",
        )
        return redirect(
            reverse(
                "kependudukan:detailKompleks",
                kwargs={"idkompleks": kompleks_id},
            )
        )

    context = {"data": data_transaksi}

    return render(
        request, template_name="delete_form_iuran_bulanan.html", context=context
    )


@login_required
@admin_or_petugas_required
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
@admin_or_petugas_required
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
@admin_or_petugas_required
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
@admin_or_petugas_required
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


@login_required
@admin_or_petugas_required
def iuranYearly(request):
    context = {}
    current_year = int(datetime.now().strftime("%Y"))
    context["range_tahun"] = [
        year for year in range(current_year, current_year - 6, -1)
    ]
    if request.POST:
        year = int(request.POST["periode_tahun"])
    else:
        year = current_year

    sum_transaksi = (
        TransaksiIuranBulanan.objects.filter(tanggal_bayar__year=year)
        .annotate(month=TruncMonth("tanggal_bayar"))
        .values("month")
        .annotate(total_amount=Sum("total_bayar"))
        .order_by("month")
    )
    grand_total = TransaksiIuranBulanan.objects.filter(
        tanggal_bayar__year=year
    ).aggregate(total_amount=Sum("total_bayar"))["total_amount"]

    context["year"] = year
    context["sum_transaksi"] = sum_transaksi
    context["grand_total"] = grand_total

    return render(request, template_name="iuran_yearly.html", context=context)


@login_required
@admin_or_petugas_required
def form_batch_iuran_bulanan(request, idkompleks, year=datetime.now().strftime("%Y")):
    data_kompleks = get_object_or_404(Kompleks, pk=idkompleks)

    if request.method == "POST":
        form = BatchIuranBulananForm(request.POST, request.FILES)
        if form.is_valid():
            selected_months = form.cleaned_data["bulan"]
            tahun = form.cleaned_data["periode_tahun"]
            total_bayar = form.cleaned_data["total_bayar"]
            keterangan = form.cleaned_data["keterangan"]
            bukti_bayar = form.cleaned_data.get("bukti_bayar")

            # Check for existing payments
            existing_months = []
            for bulan in selected_months:
                if not check_existing_trx_bulan(bulan, tahun, idkompleks):
                    existing_months.append(
                        dict(TransaksiIuranBulanan.LIST_BULAN).get(int(bulan), bulan)
                    )

            if existing_months:
                month_list = ", ".join(f"<strong>{m}</strong>" for m in existing_months)
                error_message = f"Iuran untuk bulan {month_list} tahun {tahun} sudah tercatat. Silakan hapus centang bulan tersebut dan coba lagi."
                logger.error(
                    "Duplicate batch iuran attempt: %s tahun %s"
                    % (", ".join(existing_months), tahun)
                )
                messages.error(request, error_message)
                # Re-render with the same bound form so all field values are retained
                year = tahun
            else:
                # Save transactions for each selected month
                for bulan in selected_months:
                    TransaksiIuranBulanan.objects.create(
                        kompleks=data_kompleks,
                        periode_bulan=bulan,
                        periode_tahun=tahun,
                        total_bayar=total_bayar,
                        keterangan=keterangan,
                        bukti_bayar=bukti_bayar,
                    )

                messages.success(
                    request,
                    f"Iuran bulanan untuk <strong>{len(selected_months)}</strong> bulan berhasil disimpan.",
                )
                return redirect(
                    reverse(
                        "kependudukan:detailKompleks",
                        kwargs={"idkompleks": idkompleks},
                    )
                )
        else:
            # Form validation failed (e.g. no months selected, missing total_bayar)
            logger.warning("Batch iuran form invalid: %s" % form.errors)
            messages.warning(
                request,
                "Form tidak valid. Pastikan memilih setidaknya satu bulan dan mengisi jumlah iuran.",
            )
            # year from URL param keeps the history table in sync
    else:
        form = BatchIuranBulananForm(initial={"periode_tahun": year})

    context = {
        "data_kompleks": data_kompleks,
        "year": year,
        "form": form,
        "iuran_year_period": helper_finance_year_list(),
        "default_iuran_amount": settings.IURAN_BULANAN,
        "data_iuran": TransaksiIuranBulanan.objects.filter(
            periode_tahun=year, kompleks__id=idkompleks
        ).order_by("periode_bulan"),
    }

    return render(request, "form_batch_iuran_bulanan.html", context)
