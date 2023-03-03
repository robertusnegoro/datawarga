from .forms import WargaForm, GenerateKompleksForm, WargaCSVForm
from .models import Warga, Kompleks
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core import serializers
from django.db.models import Q, Count
from django.http import HttpResponse, Http404, JsonResponse, FileResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.template.loader import render_to_string
from django.urls import reverse
from urllib.parse import urlencode
from django.core.exceptions import *
from datetime import datetime
import logging
import csv
import random

logger = logging.getLogger(__name__)


@login_required
def dashboard_warga(request):
    total_warga = Warga.objects.all().count()
    jenkel_laki = Warga.objects.filter(jenis_kelamin="LAKI-LAKI").count()
    jenkel_perempuan = Warga.objects.filter(jenis_kelamin="PEREMPUAN").count()
    data_agama = []
    for agama in Warga.RELIGIONS:
        data_agama.append(Warga.objects.filter(agama=agama[0]).count())

    data_status_tinggal = []
    for status_tinggal in Warga.STATUS_TINGGAL:
        data_status_tinggal.append(
            Warga.objects.filter(status_tinggal=status_tinggal[0]).count()
        )

    warga_per_cluster = (
        Kompleks.objects.all().values("cluster").annotate(num_warga=Count("warga"))
    )

    legend_cluster = [x["cluster"] for x in warga_per_cluster]
    data_cluster = [x["num_warga"] for x in warga_per_cluster]

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
    }
    return render(request=request, template_name="dashboard.html", context=context)


@login_required
def generate_data_warga(request, count=10):
    counter = 0

    first_name = ("Tatang", "Midun", "Yuni", "Yana", "Ucup", "Jule", "Nunung")
    last_name = ("Batagor", "Siomay", "Cilok", "Buryam", "Sambel", "Terasi")
    tempat_lahir = ("Malang", "Payakumbuh", "Medan", "Magelang")

    while counter < count:
        nama_lengkap = "%s %s" % (random.choice(first_name), random.choice(last_name))
        data_warga = Warga.objects.create(
            nama_lengkap=nama_lengkap,
            nik=random.randint(100000000, 200000000),
            agama=random.choice(Warga.RELIGIONS)[0],
            kode_pos=15315,
            no_hp=random.randint(1000000, 2000000),
            no_kk=random.randint(100000000, 200000000),
            pekerjaan=random.choice(Warga.PEKERJAAN)[0],
            status=random.choice(Warga.STATUS_KAWIN)[0],
            tanggal_lahir="%s-08-10" % (random.randint(1960, 1990)),
            tempat_lahir=random.choice(tempat_lahir),
            jenis_kelamin=random.choice(Warga.JENIS_KELAMIN)[0],
            alamat_blok="A-%s" % (random.randint(1, 5)),
            alamat_nomor=random.randint(1, 100),
            status_tinggal=random.choice(Warga.STATUS_TINGGAL)[0],
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
