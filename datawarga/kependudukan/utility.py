from .forms import WargaCSVForm
from .models import Warga, Kompleks, TransaksiIuranBulanan
from .formatters import format_rupiah
from django.conf import settings

from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Count, Sum
from django.http import HttpResponse, Http404, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from urllib.parse import urlencode
from datetime import datetime
import logging
import csv
import random

logger = logging.getLogger(__name__)


@login_required
def dashboard_warga(request):
    total_warga = Warga.objects.exclude(status_tinggal="PINDAH").count()
    ultah = Warga.objects.filter(tanggal_lahir__month=datetime.now().month).exclude(
        status_tinggal="PINDAH"
    )
    jenkel_laki = (
        Warga.objects.filter(jenis_kelamin="LAKI-LAKI")
        .exclude(status_tinggal="PINDAH")
        .count()
    )
    jenkel_perempuan = (
        Warga.objects.filter(jenis_kelamin="PEREMPUAN")
        .exclude(status_tinggal="PINDAH")
        .count()
    )
    data_agama = []
    for agama in Warga.RELIGIONS:
        data_agama.append(
            Warga.objects.filter(agama=agama[0])
            .exclude(status_tinggal="PINDAH")
            .count()
        )

    data_status_tinggal = []
    for status_tinggal in Warga.STATUS_TINGGAL:
        data_status_tinggal.append(
            Warga.objects.filter(status_tinggal=status_tinggal[0]).count()
        )

    warga_per_cluster = (
        Kompleks.objects.all().values("cluster").annotate(num_warga=Count("warga"))
    )

    legend_cluster = [
        x["cluster"] if x["cluster"] is not None else "Tanpa Cluster"
        for x in warga_per_cluster
    ]
    data_cluster = [x["num_warga"] for x in warga_per_cluster]

    # Additional metrics and statistics:
    total_kk = (
        Warga.objects.filter(kepala_keluarga=True)
        .exclude(status_tinggal="PINDAH")
        .count()
    )
    total_kompleks = Kompleks.objects.count()
    occupied_kompleks = (
        Kompleks.objects.annotate(num_warga=Count("warga"))
        .filter(num_warga__gt=0)
        .count()
    )
    vacant_kompleks = total_kompleks - occupied_kompleks

    current_year = datetime.now().year
    current_month = datetime.now().month
    current_month_name = TransaksiIuranBulanan.indonesian_months[current_month - 1]

    # Calculate financial performance for current year
    total_iuran_year = (
        TransaksiIuranBulanan.objects.filter(periode_tahun=current_year).aggregate(
            total=Sum("total_bayar")
        )["total"]
        or 0
    )
    total_iuran_year_formatted = format_rupiah(total_iuran_year)

    monthly_income = [0] * 12
    monthly_income_qs = (
        TransaksiIuranBulanan.objects.filter(periode_tahun=current_year)
        .values("periode_bulan")
        .annotate(total=Sum("total_bayar"))
    )
    for m in monthly_income_qs:
        monthly_income[m["periode_bulan"] - 1] = m["total"]

    # Current month's collection status for occupied complexes
    occupied_kompleks_ids = list(
        Warga.objects.exclude(status_tinggal="PINDAH")
        .values_list("kompleks_id", flat=True)
        .distinct()
    )
    paid_houses_count = (
        TransaksiIuranBulanan.objects.filter(
            periode_tahun=current_year,
            periode_bulan=current_month,
            kompleks_id__in=occupied_kompleks_ids,
        )
        .values("kompleks_id")
        .distinct()
        .count()
    )

    total_occupied_houses = len(occupied_kompleks_ids)
    unpaid_houses_count = total_occupied_houses - paid_houses_count
    payment_rate_pct = (
        int((paid_houses_count / total_occupied_houses) * 100)
        if total_occupied_houses > 0
        else 0
    )

    # Age distribution
    today = datetime.now().date()
    wargas_age = Warga.objects.exclude(status_tinggal="PINDAH").exclude(
        tanggal_lahir=None
    )
    age_groups = {
        "Balita (0-5)": 0,
        "Anak-anak (6-12)": 0,
        "Remaja (13-17)": 0,
        "Dewasa (18-55)": 0,
        "Lansia (56+)": 0,
    }
    for w in wargas_age:
        dob = w.tanggal_lahir
        age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
        if age <= 5:
            age_groups["Balita (0-5)"] += 1
        elif age <= 12:
            age_groups["Anak-anak (6-12)"] += 1
        elif age <= 17:
            age_groups["Remaja (13-17)"] += 1
        elif age <= 55:
            age_groups["Dewasa (18-55)"] += 1
        else:
            age_groups["Lansia (56+)"] += 1

    legend_umur = list(age_groups.keys())
    data_umur = list(age_groups.values())

    context = {
        "legend_agama": [agama[0] for agama in Warga.RELIGIONS],
        "legend_jenkel": [jk[0] for jk in Warga.JENIS_KELAMIN],
        "legend_status_tinggal": [
            status_tinggal[0] for status_tinggal in Warga.STATUS_TINGGAL
        ],
        "legend_cluster": legend_cluster,
        "data_cluster": data_cluster,
        "data_jenkel": [jenkel_laki, jenkel_perempuan],
        "data_agama": data_agama,
        "data_status_tinggal": data_status_tinggal,
        "total_warga": total_warga,
        "ultah": ultah,
        # New enriched context variables:
        "total_kk": total_kk,
        "total_kompleks": total_kompleks,
        "occupied_kompleks": occupied_kompleks,
        "vacant_kompleks": vacant_kompleks,
        "total_iuran_year": total_iuran_year,
        "total_iuran_year_formatted": total_iuran_year_formatted,
        "paid_houses_count": paid_houses_count,
        "unpaid_houses_count": unpaid_houses_count,
        "payment_rate_pct": payment_rate_pct,
        "monthly_income": monthly_income,
        "legend_umur": legend_umur,
        "data_umur": data_umur,
        "current_year": current_year,
        "current_month_name": current_month_name,
    }
    return render(request=request, template_name="dashboard.html", context=context)


@login_required
def statistic_warga(request):
    all_data = (
        Warga.objects.values("kompleks__rt", "kompleks__rw")
        .annotate(num_warga=Count("id"))
        .exclude(status_tinggal="PINDAH")
        .exclude(agama=None)
        .exclude(jenis_kelamin=None)
        .exclude(status_tinggal=None)
        .order_by("kompleks__rt", "kompleks__rw")
    )

    jenis_kelamin = (
        Warga.objects.values("kompleks__rt", "kompleks__rw", "jenis_kelamin")
        .annotate(num_warga=Count("id"))
        .exclude(status_tinggal="PINDAH")
        .exclude(agama=None)
        .exclude(jenis_kelamin=None)
        .exclude(status_tinggal=None)
        .order_by("kompleks__rt", "kompleks__rw", "jenis_kelamin")
    )

    agama = (
        Warga.objects.values("kompleks__rt", "kompleks__rw", "agama")
        .annotate(num_warga=Count("id"))
        .exclude(status_tinggal="PINDAH")
        .exclude(agama=None)
        .exclude(jenis_kelamin=None)
        .exclude(status_tinggal=None)
        .order_by("kompleks__rt", "kompleks__rw", "agama")
    )

    status_tinggal = (
        Warga.objects.values("kompleks__rt", "kompleks__rw", "status_tinggal")
        .annotate(num_warga=Count("id"))
        .exclude(status_tinggal="PINDAH")
        .exclude(agama=None)
        .exclude(jenis_kelamin=None)
        .exclude(status_tinggal=None)
        .order_by("kompleks__rt", "kompleks__rw", "status_tinggal")
    )

    warga_pindah = (
        Warga.objects.filter(status_tinggal="PINDAH")
        .values("kompleks__rt", "kompleks__rw")
        .annotate(num_warga=Count("id"))
        .exclude(agama=None)
        .exclude(jenis_kelamin=None)
        .exclude(status_tinggal=None)
        .order_by("kompleks__rt", "kompleks__rw")
    )

    kepala_keluarga = (
        Warga.objects.filter(kepala_keluarga=True)
        .values("kompleks__rt", "kompleks__rw")
        .annotate(num_warga=Count("id"))
        .exclude(agama=None)
        .exclude(jenis_kelamin=None)
        .exclude(status_tinggal=None)
        .order_by("kompleks__rt", "kompleks__rw")
    )

    context = {
        "jenis_kelamin": jenis_kelamin,
        "agama": agama,
        "status_tinggal": status_tinggal,
        "all_data": all_data,
        "warga_pindah": warga_pindah,
        "kepala_keluarga": kepala_keluarga,
    }

    return render(
        request=request, template_name="statistic_warga.html", context=context
    )


@user_passes_test(lambda u: u.is_superuser)
def generate_data_warga(request, count=10):
    counter = 0

    first_name = ("Tatang", "Midun", "Yuni", "Yana", "Ucup", "Jule", "Nunung")
    last_name = ("Batagor", "Siomay", "Cilok", "Buryam", "Sambel", "Terasi")
    tempat_lahir = ("Malang", "Payakumbuh", "Medan", "Magelang")

    while counter < count:
        random_records = list(Kompleks.objects.all())
        random_komplek = random.sample(random_records, 1)[0]
        nama_lengkap = "%s %s" % (random.choice(first_name), random.choice(last_name))
        Warga.objects.create(
            nama_lengkap=nama_lengkap,
            nik=random.randint(100000000, 200000000),
            agama=random.choice(Warga.RELIGIONS)[0],
            no_hp=random.randint(1000000, 2000000),
            no_kk=random.randint(100000000, 200000000),
            pekerjaan=random.choice(Warga.PEKERJAAN)[0],
            status=random.choice(Warga.STATUS_KAWIN)[0],
            tanggal_lahir="%s-08-10" % (random.randint(1960, 1990)),
            tempat_lahir=random.choice(tempat_lahir),
            jenis_kelamin=random.choice(Warga.JENIS_KELAMIN)[0],
            status_tinggal=random.choice(Warga.STATUS_TINGGAL)[0],
            kompleks=random_komplek,
        )
        counter += 1
    return HttpResponse("generated %s data" % (counter))


@login_required
def import_data_warga_form(request):
    if request.POST:
        form = WargaCSVForm(request.POST, request.FILES)
        if form.is_valid():
            csv_file = request.FILES["csv_file"]
            data_set = csv_file.read().decode("UTF-8")
            csv_reader = csv.DictReader(data_set.splitlines(), delimiter=",")

            data_list = []

            for row in csv_reader:
                logger.info(row)

                status_keluarga_val = row.get("status_keluarga")
                if status_keluarga_val is not None:
                    status_keluarga_val = str(status_keluarga_val).strip().upper()
                    valid_choices = [c[0] for c in Warga.STATUS_KELUARGA]
                    if status_keluarga_val not in valid_choices:
                        status_keluarga_val = "N/A"
                else:
                    status_keluarga_val = "N/A"

                data_list.append(
                    Warga(
                        agama=str(row["agama"]).upper(),
                        nama_lengkap=row["nama_lengkap"],
                        nik=row["nik"],
                        no_hp=row["no_hp"],
                        no_kk=row["no_kk"],
                        pekerjaan=str(row["pekerjaan"]).upper(),
                        status=str(row["status_kawin"]).upper(),
                        tanggal_lahir=str(row["tanggal_lahir"]),
                        tempat_lahir=row["tempat_lahir"],
                        jenis_kelamin=str(row["jenis_kelamin"]).upper(),
                        status_tinggal=str(row["status_tinggal"]).upper(),
                        alamat_ktp=row["alamat_ktp"],
                        status_keluarga=status_keluarga_val,
                        kompleks=None,
                    )
                )
            try:
                Warga.objects.bulk_create(data_list)
                base_url = reverse("kependudukan:listWargaView")
                payload = urlencode({"message": "data saved!"})
                url_redir = "{}?{}".format(base_url, payload)
                return redirect(url_redir)
            except Exception as ex:
                return HttpResponse(ex)
        else:
            logger.info(form.errors)
            return HttpResponse("form is not valid %s" % (form.errors))
    else:
        form = WargaCSVForm()

    context = {
        "form": form,
        "agama": Warga.RELIGIONS,
        "status_kawin": Warga.STATUS_KAWIN,
        "status_tinggal": Warga.STATUS_TINGGAL,
        "pekerjaan": Warga.PEKERJAAN,
        "jenis_kelamin": Warga.JENIS_KELAMIN,
        "status_keluarga": Warga.STATUS_KELUARGA,
    }

    return render(
        request=request, template_name="form_export_warga.html", context=context
    )


@login_required
def assign_warga_rumah(request):
    return render(request=request, template_name="form_assign_warga_rumah.html")


@login_required
def assign_warga_rumah_exec(request):
    if request.POST:
        list_warga_ids = request.POST.getlist("warga_ids[]")
        idkompleks = request.POST["idkompleks"]

        data_kompleks = get_object_or_404(Kompleks, pk=idkompleks)

        for w in list_warga_ids:
            data_warga = Warga.objects.get(pk=w)
            data_warga.kompleks = data_kompleks
            data_warga.save()
            logger.info("Data warga %s telah diassign ke rumah %s" % (w, idkompleks))

        return JsonResponse(
            {"status": "ok", "message": "data warga berhasil di-assign ke rumah"}
        )
    return Http404


def helper_finance_year_list():
    iuran_start_period = settings.FINANCE_PERIOD_START
    iuran_current_period = int(datetime.now().strftime("%Y"))

    return [x for x in reversed(range(iuran_start_period, (iuran_current_period + 1)))]


def dashboard_public(request, page="warga"):
    context = {}
    if page == "warga":
        context["total_warga"] = Warga.objects.all().count()
    elif page == "jenis_kelamin":
        jenkel_laki = Warga.objects.filter(jenis_kelamin="LAKI-LAKI").count()
        jenkel_perempuan = Warga.objects.filter(jenis_kelamin="PEREMPUAN").count()
        context["legend_jenkel"] = [jk[0] for jk in Warga.JENIS_KELAMIN]
        context["data_jenkel"] = [jenkel_laki, jenkel_perempuan]
    elif page == "agama":
        data_agama = []
        for agama in Warga.RELIGIONS:
            data_agama.append(Warga.objects.filter(agama=agama[0]).count())
        context["legend_agama"] = [agama[0] for agama in Warga.RELIGIONS]
        context["data_agama"] = data_agama
    elif page == "status_tinggal":
        data_status_tinggal = []
        for status_tinggal in Warga.STATUS_TINGGAL:
            data_status_tinggal.append(
                Warga.objects.filter(status_tinggal=status_tinggal[0]).count()
            )
        context["legend_status_tinggal"] = [
            status_tinggal[0] for status_tinggal in Warga.STATUS_TINGGAL
        ]
        context["data_status_tinggal"] = data_status_tinggal
    elif page == "cluster":
        warga_per_cluster = (
            Kompleks.objects.all().values("cluster").annotate(num_warga=Count("warga"))
        )

        context["legend_cluster"] = [
            x["cluster"] if x["cluster"] is not None else "Tanpa Cluster"
            for x in warga_per_cluster
        ]
        context["data_cluster"] = [x["num_warga"] for x in warga_per_cluster]
    else:
        return Http404

    template_path = "public/dashboard_%s.html" % (page)
    return render(request=request, template_name=template_path, context=context)
