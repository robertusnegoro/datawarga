from .forms import WargaForm, GenerateKompleksForm, WargaCSVForm
from .models import Warga, Kompleks
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core import serializers
from django.db.models import Q
from django.http import HttpResponse, Http404, JsonResponse, FileResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.template.loader import render_to_string
from django.urls import reverse
from django.views.static import serve
from urllib.parse import urlencode
import logging
import csv

logger = logging.getLogger(__name__)


@login_required
def import_data_warga_form(request):
    if request.POST:
        form = WargaCSVForm(request.POST, request.FILES)
        if form.is_valid():
            csv_file = request.FILES["csv_file"]
            data_set = csv_file.read().decode('UTF-8')
            csv_reader = csv.DictReader(data_set.splitlines(), delimiter=',')
            
            data_list = []

            for row in csv_reader:
                logger.info(row)
                data_list.append(Warga(
                    agama=str(row['agama']).upper(),
                    nama_lengkap=row['nama_lengkap'],
                    nik=row['nik'],
                    no_hp=row['no_hp'],
                    no_kk=row['no_kk'],
                    pekerjaan=str(row['pekerjaan']).upper(),
                    status=str(row['status_kawin']).upper(),
                    tanggal_lahir=str(row['tanggal_lahir']),
                    tempat_lahir=row["tempat_lahir"],
                    jenis_kelamin=str(row['jenis_kelamin']).upper(),
                    status_tinggal=str(row["status_tinggal"]).upper(),
                    alamat_ktp=row["alamat_ktp"],
                    kompleks=None
                ))
            Warga.objects.bulk_create(data_list)
            base_url = reverse("kependudukan:listWargaView")
            payload = urlencode({"message": "data saved!"})
            url_redir = "{}?{}".format(base_url, payload)
            return redirect(url_redir)
        else:
            logger.info(form.errors)
            return HttpResponse("form is not valid %s" % (form.errors))
    else:
        form = WargaCSVForm()

    context = {
        'form': form,
        'agama': Warga.RELIGIONS,
        'status_kawin': Warga.STATUS_KAWIN,
        'status_tinggal': Warga.STATUS_TINGGAL,
        'pekerjaan': Warga.PEKERJAAN,
        'jenis_kelamin': Warga.JENIS_KELAMIN
    }

    return render(
        request=request, template_name="form_export_warga.html", context=context
    )
