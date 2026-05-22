from datetime import date, datetime
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from django.template.loader import render_to_string
from django.db.models import Sum, Q
from django.contrib import messages
from functools import wraps
from weasyprint import HTML
from weasyprint.text.fonts import FontConfiguration
from django.conf import settings

from kependudukan.models import KasTransaksi, KasTagihan, TransaksiIuranBulanan
from kependudukan.forms import KasTransaksiForm, KasTagihanForm
from kependudukan.context_processors import kas_permissions


def kas_access_required(view_func):
    """
    Decorator that checks if the logged-in user is a bendahara, rt_pic, or superuser.
    Fails closed by returning a 403 Forbidden response.
    """

    @login_required
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        perms = kas_permissions(request)
        if perms.get("is_kas_user"):
            return view_func(request, *args, **kwargs)
        raise PermissionDenied(
            "Anda tidak memiliki akses ke fitur Keuangan & Kas RT/RW."
        )

    return _wrapped_view


@kas_access_required
def dashboard_kas(request):
    """
    Financial dashboard displaying key cash metrics, Chart.js visuals,
    unpaid bills, and recent transactions.
    """
    # Summary Metrics
    total_pemasukan = (
        KasTransaksi.objects.filter(jenis="PEMASUKAN").aggregate(total=Sum("jumlah"))[
            "total"
        ]
        or 0
    )
    total_pengeluaran = (
        KasTransaksi.objects.filter(jenis="PENGELUARAN").aggregate(total=Sum("jumlah"))[
            "total"
        ]
        or 0
    )
    saldo = total_pemasukan - total_pengeluaran

    piutang_belum = (
        KasTagihan.objects.filter(jenis="PIUTANG", status="BELUM").aggregate(
            total=Sum("jumlah")
        )["total"]
        or 0
    )
    hutang_belum = (
        KasTagihan.objects.filter(jenis="HUTANG", status="BELUM").aggregate(
            total=Sum("jumlah")
        )["total"]
        or 0
    )

    # Recent Records
    recent_transactions = KasTransaksi.objects.all().order_by("-tanggal", "-id")[:5]
    recent_bills = KasTagihan.objects.all().order_by("tanggal_jatuh_tempo")[:5]

    # Calculate date.today() for template comparison
    today = date.today()

    # Chart.js Data: Monthly Trend for the current year
    current_year = today.year
    monthly_pemasukan = [0] * 12
    monthly_pengeluaran = [0] * 12

    pemasukan_qs = (
        KasTransaksi.objects.filter(tanggal__year=current_year, jenis="PEMASUKAN")
        .values("tanggal__month")
        .annotate(total=Sum("jumlah"))
    )
    for item in pemasukan_qs:
        m = item["tanggal__month"]
        monthly_pemasukan[m - 1] = item["total"]

    pengeluaran_qs = (
        KasTransaksi.objects.filter(tanggal__year=current_year, jenis="PENGELUARAN")
        .values("tanggal__month")
        .annotate(total=Sum("jumlah"))
    )
    for item in pengeluaran_qs:
        m = item["tanggal__month"]
        monthly_pengeluaran[m - 1] = item["total"]

    # Chart.js Data: Category breakdown
    cat_pemasukan = (
        KasTransaksi.objects.filter(jenis="PEMASUKAN")
        .values("kategori")
        .annotate(total=Sum("jumlah"))
    )
    cat_pengeluaran = (
        KasTransaksi.objects.filter(jenis="PENGELUARAN")
        .values("kategori")
        .annotate(total=Sum("jumlah"))
    )

    cat_pemasukan_labels = [c["kategori"] for c in cat_pemasukan]
    cat_pemasukan_data = [c["total"] for c in cat_pemasukan]

    cat_pengeluaran_labels = [c["kategori"] for c in cat_pengeluaran]
    cat_pengeluaran_data = [c["total"] for c in cat_pengeluaran]

    context = {
        "total_pemasukan": total_pemasukan,
        "total_pengeluaran": total_pengeluaran,
        "saldo": saldo,
        "piutang_belum": piutang_belum,
        "hutang_belum": hutang_belum,
        "recent_transactions": recent_transactions,
        "recent_bills": recent_bills,
        "today": today,
        "current_year": current_year,
        "monthly_pemasukan": monthly_pemasukan,
        "monthly_pengeluaran": monthly_pengeluaran,
        "cat_pemasukan_labels": cat_pemasukan_labels,
        "cat_pemasukan_data": cat_pemasukan_data,
        "cat_pengeluaran_labels": cat_pengeluaran_labels,
        "cat_pengeluaran_data": cat_pengeluaran_data,
    }
    return render(request, "kas/dashboard.html", context)


@kas_access_required
def list_kas_transaksi(request):
    """
    Renders cash transaction list with robust filters (by type, category, date) and pagination.
    """
    queryset = KasTransaksi.objects.all().order_by("-tanggal", "-id")

    # Filters
    jenis = request.GET.get("jenis")
    kategori = request.GET.get("kategori")
    start_date = request.GET.get("start_date")
    end_date = request.GET.get("end_date")

    if jenis:
        queryset = queryset.filter(jenis=jenis)
    if kategori:
        queryset = queryset.filter(kategori=kategori)
    if start_date:
        try:
            queryset = queryset.filter(tanggal__gte=start_date)
        except ValueError:
            pass
    if end_date:
        try:
            queryset = queryset.filter(tanggal__lte=end_date)
        except ValueError:
            pass

    # Aggregates for filtered result
    totals = queryset.aggregate(
        total_pemasukan=Sum("jumlah", filter=Q(jenis="PEMASUKAN")),
        total_pengeluaran=Sum("jumlah", filter=Q(jenis="PENGELUARAN")),
    )
    total_pemasukan = totals["total_pemasukan"] or 0
    total_pengeluaran = totals["total_pengeluaran"] or 0

    # Pagination
    from django.core.paginator import Paginator

    paginator = Paginator(queryset, 20)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {
        "transaksi_list": page_obj,
        "page_obj": page_obj,
        "jenis_choices": KasTransaksi.JENIS_CHOICES,
        "kategori_choices": KasTransaksi.KATEGORI_CHOICES,
        "selected_jenis": jenis,
        "selected_kategori": kategori,
        "selected_start_date": start_date,
        "selected_end_date": end_date,
        "total_pemasukan": total_pemasukan,
        "total_pengeluaran": total_pengeluaran,
        "net_amount": total_pemasukan - total_pengeluaran,
        "net_amount_abs": abs(total_pemasukan - total_pengeluaran),
    }
    return render(request, "kas/transaksi_list.html", context)


@kas_access_required
def form_kas_transaksi(request, idtransaksi=None):
    """
    Handles creating or updating a general ledger transaction.
    """
    instance = get_object_or_404(KasTransaksi, pk=idtransaksi) if idtransaksi else None

    if request.method == "POST":
        form = KasTransaksiForm(request.POST, request.FILES, instance=instance)
        if form.is_valid():
            form.save()
            messages.success(request, "Transaksi kas berhasil disimpan.")
            return redirect(reverse("kependudukan:list_kas_transaksi"))
    else:
        form = KasTransaksiForm(instance=instance)

    context = {
        "form": form,
        "instance": instance,
    }
    return render(request, "kas/transaksi_form.html", context)


@kas_access_required
def delete_kas_transaksi(request, idtransaksi):
    """
    Asks confirmation and deletes a transaction.
    """
    instance = get_object_or_404(KasTransaksi, pk=idtransaksi)

    if request.method == "POST":
        instance.delete()
        messages.success(request, "Transaksi kas berhasil dihapus.")
        return redirect(reverse("kependudukan:list_kas_transaksi"))

    return render(
        request, "kas/delete_confirm.html", {"instance": instance, "type": "transaksi"}
    )


@kas_access_required
def list_kas_tagihan(request):
    """
    Renders bills list with filters (status, type, kategori, date range) and pagination.
    """
    queryset = KasTagihan.objects.all().order_by("status", "tanggal_jatuh_tempo")

    # Filters
    status = request.GET.get("status")
    jenis = request.GET.get("jenis")
    kategori = request.GET.get("kategori")
    start_date = request.GET.get("start_date")
    end_date = request.GET.get("end_date")

    if status:
        queryset = queryset.filter(status=status)
    if jenis:
        queryset = queryset.filter(jenis=jenis)
    if kategori:
        queryset = queryset.filter(kategori=kategori)
    if start_date:
        try:
            queryset = queryset.filter(tanggal_jatuh_tempo__gte=start_date)
        except ValueError:
            pass
    if end_date:
        try:
            queryset = queryset.filter(tanggal_jatuh_tempo__lte=end_date)
        except ValueError:
            pass

    # Pagination
    from django.core.paginator import Paginator

    paginator = Paginator(queryset, 20)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {
        "tagihan_list": page_obj,
        "page_obj": page_obj,
        "status_choices": KasTagihan.STATUS_CHOICES,
        "jenis_choices": KasTagihan.JENIS_CHOICES,
        "kategori_choices": KasTagihan.KATEGORI_CHOICES,
        "selected_status": status,
        "selected_jenis": jenis,
        "selected_kategori": kategori,
        "selected_start_date": start_date,
        "selected_end_date": end_date,
        "today": date.today(),
    }
    return render(request, "kas/tagihan_list.html", context)


@kas_access_required
def form_kas_tagihan(request, idtagihan=None):
    """
    Handles creating or updating a pending bill.
    """
    instance = get_object_or_404(KasTagihan, pk=idtagihan) if idtagihan else None

    if request.method == "POST":
        form = KasTagihanForm(request.POST, instance=instance)
        if form.is_valid():
            form.save()
            messages.success(request, "Data tagihan/invoice berhasil disimpan.")
            return redirect(reverse("kependudukan:list_kas_tagihan"))
    else:
        form = KasTagihanForm(instance=instance)

    context = {
        "form": form,
        "instance": instance,
    }
    return render(request, "kas/tagihan_form.html", context)


@kas_access_required
def delete_kas_tagihan(request, idtagihan):
    """
    Asks confirmation and deletes a bill.
    """
    instance = get_object_or_404(KasTagihan, pk=idtagihan)

    if request.method == "POST":
        instance.delete()
        messages.success(request, "Data tagihan berhasil dihapus.")
        return redirect(reverse("kependudukan:list_kas_tagihan"))

    return render(
        request, "kas/delete_confirm.html", {"instance": instance, "type": "tagihan"}
    )


@kas_access_required
def bayar_tagihan(request, idtagihan):
    """
    Marks a bill as paid (Lunas) and automatically creates a corresponding
    transaction record in the general ledger.
    """
    bill = get_object_or_404(KasTagihan, pk=idtagihan)
    if bill.status == "LUNAS":
        messages.warning(request, "Tagihan ini sudah lunas.")
        return redirect(reverse("kependudukan:list_kas_tagihan"))

    # Update bill status
    bill.status = "LUNAS"
    bill.save()

    # Automatically generate transaction
    jenis_tx = "PEMASUKAN" if bill.jenis == "PIUTANG" else "PENGELUARAN"
    keterangan_tx = f"Pelunasan tagihan: {bill.judul}"
    if bill.keterangan:
        keterangan_tx += f" ({bill.keterangan})"

    KasTransaksi.objects.create(
        tanggal=date.today(),
        jenis=jenis_tx,
        kategori=bill.kategori,
        jumlah=bill.jumlah,
        keterangan=keterangan_tx,
        tagihan_asal=bill,
    )

    messages.success(
        request,
        f"Tagihan '{bill.judul}' berhasil dilunasi. Transaksi kas otomatis telah dibuat.",
    )
    return redirect(reverse("kependudukan:list_kas_tagihan"))


@kas_access_required
def sync_iuran_to_kas(request):
    """
    Batch synchronization to import existing TransaksiIuranBulanan payments
    into KasTransaksi general ledger.
    """
    iurans = TransaksiIuranBulanan.objects.all()
    count_created = 0
    count_updated = 0

    for item in iurans:
        keterangan_auto = (
            item.keterangan
            or f"Iuran Bulanan RT/RW - Kompleks {item.kompleks} (Bulan {item.periode_bulan}, Tahun {item.periode_tahun})"
        )
        kas, created = KasTransaksi.objects.update_or_create(
            iuran_asal=item,
            defaults={
                "tanggal": item.tanggal_bayar,
                "jenis": "PEMASUKAN",
                "kategori": "IURAN",
                "jumlah": item.total_bayar,
                "keterangan": keterangan_auto,
                "bukti_transaksi": item.bukti_bayar if item.bukti_bayar else None,
            },
        )
        if created:
            count_created += 1
        else:
            count_updated += 1

    messages.success(
        request,
        f"Sinkronisasi selesai. {count_created} data kas baru dibuat, {count_updated} data diperbarui.",
    )
    return redirect(reverse("kependudukan:dashboard_kas"))


@kas_access_required
def pdf_report_kas(request):
    """
    Generates a download-ready PDF financial report using WeasyPrint.
    """
    start_date = request.GET.get("start_date")
    end_date = request.GET.get("end_date")

    # Default to current month if no parameters are supplied in URL (e.g. fresh load)
    if start_date is None and end_date is None:
        today = date.today()
        start_date = today.replace(day=1).strftime("%Y-%m-%d")
        import calendar

        last_day = calendar.monthrange(today.year, today.month)[1]
        end_date = today.replace(day=last_day).strftime("%Y-%m-%d")
    else:
        if start_date == "":
            start_date = None
        if end_date == "":
            end_date = None

    # Calculate Saldo Awal (cumulative net balance before start_date)
    saldo_awal = 0
    if start_date:
        total_pemasukan_sebelum = (
            KasTransaksi.objects.filter(
                tanggal__lt=start_date, jenis="PEMASUKAN"
            ).aggregate(total=Sum("jumlah"))["total"]
            or 0
        )

        total_pengeluaran_sebelum = (
            KasTransaksi.objects.filter(
                tanggal__lt=start_date, jenis="PENGELUARAN"
            ).aggregate(total=Sum("jumlah"))["total"]
            or 0
        )

        saldo_awal = total_pemasukan_sebelum - total_pengeluaran_sebelum

    # Get transactions within the period
    queryset = KasTransaksi.objects.all().order_by("tanggal", "id")
    if start_date:
        queryset = queryset.filter(tanggal__gte=start_date)
    if end_date:
        queryset = queryset.filter(tanggal__lte=end_date)

    totals = queryset.aggregate(
        total_pemasukan=Sum("jumlah", filter=Q(jenis="PEMASUKAN")),
        total_pengeluaran=Sum("jumlah", filter=Q(jenis="PENGELUARAN")),
    )
    total_pemasukan = totals["total_pemasukan"] or 0
    total_pengeluaran = totals["total_pengeluaran"] or 0
    saldo_akhir = saldo_awal + total_pemasukan - total_pengeluaran

    context = {
        "transaksi_list": queryset,
        "saldo_awal": saldo_awal,
        "total_pemasukan": total_pemasukan,
        "total_pengeluaran": total_pengeluaran,
        "saldo_akhir": saldo_akhir,
        "net_amount": total_pemasukan - total_pengeluaran,
        "net_amount_abs": abs(total_pemasukan - total_pengeluaran),
        "start_date": start_date,
        "end_date": end_date,
        "print_date": datetime.now(),
        "rt": settings.RUKUNTANGGA,
        "rw": settings.RUKUNWARGA,
        "kelurahan": settings.KELURAHAN,
        "kecamatan": settings.KECAMATAN,
        "kota": settings.KOTA,
    }

    # Generate PDF via WeasyPrint
    response = HttpResponse(content_type="application/pdf")
    filename = f"laporan_keuangan_kas_rt{settings.RUKUNTANGGA}.pdf"
    response["Content-Disposition"] = f"attachment; filename={filename}"

    html = render_to_string("kas/report_pdf.html", context, request=request)
    font_config = FontConfiguration()
    HTML(string=html, base_url=request.build_absolute_uri("/")).write_pdf(
        response, font_config=font_config
    )
    return response


@kas_access_required
def laporan_kas(request):
    """
    Renders standalone financial report (Laporan Keuangan) with initial balance,
    inflows, outflows, and cutoff ending balance calculations.
    """
    start_date = request.GET.get("start_date")
    end_date = request.GET.get("end_date")

    # Default to current month if no parameters are supplied in URL (e.g. fresh load)
    if start_date is None and end_date is None:
        today = date.today()
        start_date = today.replace(day=1).strftime("%Y-%m-%d")
        import calendar

        last_day = calendar.monthrange(today.year, today.month)[1]
        end_date = today.replace(day=last_day).strftime("%Y-%m-%d")
    else:
        if start_date == "":
            start_date = None
        if end_date == "":
            end_date = None

    # Calculate Saldo Awal (cumulative net balance before start_date)
    saldo_awal = 0
    if start_date:
        total_pemasukan_sebelum = (
            KasTransaksi.objects.filter(
                tanggal__lt=start_date, jenis="PEMASUKAN"
            ).aggregate(total=Sum("jumlah"))["total"]
            or 0
        )

        total_pengeluaran_sebelum = (
            KasTransaksi.objects.filter(
                tanggal__lt=start_date, jenis="PENGELUARAN"
            ).aggregate(total=Sum("jumlah"))["total"]
            or 0
        )

        saldo_awal = total_pemasukan_sebelum - total_pengeluaran_sebelum

    # Get transactions within the period
    queryset = KasTransaksi.objects.all().order_by("tanggal", "id")
    if start_date:
        queryset = queryset.filter(tanggal__gte=start_date)
    if end_date:
        queryset = queryset.filter(tanggal__lte=end_date)

    totals = queryset.aggregate(
        total_pemasukan=Sum("jumlah", filter=Q(jenis="PEMASUKAN")),
        total_pengeluaran=Sum("jumlah", filter=Q(jenis="PENGELUARAN")),
    )
    total_pemasukan = totals["total_pemasukan"] or 0
    total_pengeluaran = totals["total_pengeluaran"] or 0
    saldo_akhir = saldo_awal + total_pemasukan - total_pengeluaran

    # Pagination: limit to 20 entries
    from django.core.paginator import Paginator

    paginator = Paginator(queryset, 20)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {
        "transaksi_list": page_obj,
        "page_obj": page_obj,
        "saldo_awal": saldo_awal,
        "total_pemasukan": total_pemasukan,
        "total_pengeluaran": total_pengeluaran,
        "saldo_akhir": saldo_akhir,
        "selected_start_date": start_date,
        "selected_end_date": end_date,
        "net_amount": total_pemasukan - total_pengeluaran,
        "net_amount_abs": abs(total_pemasukan - total_pengeluaran),
    }
    return render(request, "kas/laporan.html", context)
