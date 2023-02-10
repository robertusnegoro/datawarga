from .forms import WargaForm, GenerateKompleksForm
from .models import Warga, Kompleks
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core import serializers
from django.db.models import Q
from django.http import HttpResponse, Http404, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views.generic import ListView
from django.views.static import serve
from urllib.parse import urlencode
from weasyprint import HTML
from weasyprint.text.fonts import FontConfiguration
import logging
import json

logger = logging.getLogger(__name__)


@login_required
def kompleks_form(request):
    context = {
        "rt": settings.RUKUNTANGGA,
        "rw": settings.RUKUNWARGA,
        "alamat": settings.ALAMAT,
        "kecamatan": settings.KECAMATAN,
        "kelurahan": settings.KELURAHAN,
        "kota": settings.KOTA,
        "provinsi": settings.PROVINSI,
    }
    return render(request=request, template_name="form_kompleks.html", context=context)


@login_required
def generate_kompleks(request):
    if request.POST:
        form = GenerateKompleksForm(request.POST)

        if form.is_valid():
            cluster = str(request.POST["cluster"])
            blok = str(request.POST["blok"])
            rt = str(request.POST["rt"])
            rw = str(request.POST["rw"])
            start_num = int(request.POST["start_num"])
            finish_num = int(request.POST["finish_num"])
            alamat = str(request.POST["alamat"])
            kecamatan = str(request.POST["kecamatan"])
            kelurahan = str(request.POST["kelurahan"])
            kota = str(request.POST["kota"])
            provinsi = str(request.POST["provinsi"])
            kode_pos = str(request.POST["kode_pos"])

            total_num = finish_num - start_num

            if total_num > settings.GENERATE_KOMPLEKS_LIMIT:
                logger.error(
                    "user is trying to generate more than %s data kompleks rumah."
                    % (settings.GENERATE_KOMPLEKS_LIMIT)
                )
                return HttpResponse(
                    "Error. User seharusnya tidak mengenerate lebih dari %s nomor rumah."
                    % (settings.GENERATE_KOMPLEKS_LIMIT)
                )

            counter = start_num
            while counter <= finish_num:
                Kompleks.objects.create(
                    cluster=cluster,
                    blok=blok,
                    rt=rt,
                    rw=rw,
                    nomor=counter,
                    alamat=alamat,
                    kecamatan=kecamatan,
                    kelurahan=kelurahan,
                    kota=kota,
                    provinsi=provinsi,
                    kode_pos=kode_pos,
                )
                logger.info("%s, %s, %s is saved to db" % (cluster, blok, counter))
                counter += 1
            base_url = reverse("kependudukan:listKompleksView")
            payload = urlencode(
                {
                    "message": "data blok %s sebanyak %s nomor rumah telah disimpan!"
                    % (blok, total_num)
                }
            )
            url_redir = "{}?{}".format(base_url, payload)
            return redirect(url_redir)
        else:
            logger.info(form.errors)
            return HttpResponse("form is not valid %s" % (form.errors))
    else:
        return Http404()


@method_decorator(login_required, name="dispatch")
class KompleksListView(ListView):
    paginate_by = 50
    template_name = "list_kompleks_view.html"
    queryset = Kompleks.objects.order_by("-id")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if "message" in self.request.GET:
            context["message"] = self.request.GET["message"]
        return context

    def get_queryset(self):
        queryset = super().get_queryset()
        if "search" in self.request.GET:
            search_keyword = str(self.request.GET["search"])

            queryset = queryset.filter(
                Q(cluster__icontains=search_keyword) | Q(blok__icontains=search_keyword)
            )
        return queryset


@login_required
def delete_blok_form(request):
    if request.POST:
        blok = str(request.POST["blok"])
        data_blok = Kompleks.objects.filter(blok=blok)
        jumlah_data = len(data_blok)
        if jumlah_data == 0:
            return HttpResponse("Tidak ada yang dihapus, klik back")
        data_blok.delete()
        logger.info("Deleting data kompleks blok %s " % (blok))
        base_url = reverse("kependudukan:listKompleksView")
        payload = urlencode(
            {
                "message": "data blok %s sebanyak %s nomor rumah telah dihapus!"
                % (blok, jumlah_data)
            }
        )
        url_redir = "{}?{}".format(base_url, payload)
        return redirect(url_redir)
    else:
        return render(request=request, template_name="delete_blok_form.html")


@login_required
def detail_kompleks(request, idkompleks):
    data_kompleks = get_object_or_404(Kompleks, pk=idkompleks)
    context = {}
    if request.POST:
        cluster = str(request.POST["cluster"])
        blok = str(request.POST["blok"])
        rt = str(request.POST["rt"])
        rw = str(request.POST["rw"])
        nomor = str(request.POST["nomor"])
        description = str(request.POST["description"])
        alamat = str(request.POST["alamat"])
        kecamatan = str(request.POST["kecamatan"])
        kelurahan = str(request.POST["kelurahan"])
        kota = str(request.POST["kota"])
        provinsi = str(request.POST["provinsi"])
        kode_pos = str(request.POST["kode_pos"])

        data_kompleks.cluster = cluster
        data_kompleks.blok = blok
        data_kompleks.rt = rt
        data_kompleks.rw = rw
        data_kompleks.nomor = nomor
        data_kompleks.description = description
        data_kompleks.alamat = alamat
        data_kompleks.kecamatan = kecamatan
        data_kompleks.kelurahan = kelurahan
        data_kompleks.kota = kota
        data_kompleks.provinsi = provinsi
        data_kompleks.kode_pos = kode_pos
        data_kompleks.save()

        context["message"] = "Data %s/%s telah disimpan" % (blok, nomor)
        logger.info(context["message"])

    context["data"] = data_kompleks
    context["load_url"] = reverse(
        "kependudukan:wargaRumah", kwargs={"idkompleks": idkompleks}
    )
    return render(
        request=request, template_name="form_kompleks_detail.html", context=context
    )


@login_required
def warga_rumah(request, idkompleks):
    data_warga = Warga.objects.filter(kompleks=idkompleks)
    total_warga = len(data_warga)
    data = serializers.serialize("json", data_warga)
    response = {"data": json.loads(data), "total": total_warga}
    return JsonResponse(response)


@login_required
def delete_rumah_form(request, idkompleks):
    data_kompleks = get_object_or_404(Kompleks, pk=idkompleks)
    context = {"data_kompleks": data_kompleks}
    if request.POST:
        logger.info(
            "Deleting data rumah with id : %s , data : %s" % (idkompleks, data_kompleks)
        )
        base_url = reverse("kependudukan:listKompleksView")
        payload = urlencode({"message": "data %s was deleted!" % (data_kompleks)})
        data_kompleks.delete()
        url_redir = "{}?{}".format(base_url, payload)
        return redirect(url_redir)
    return render(
        request=request, template_name="delete_form_rumah.html", context=context
    )


@login_required
def list_kompleks_json(request):
    data_kompleks = Kompleks.objects.order_by("id")
    if request.POST:
        search_keyword = str(request.POST["kompleks_search_keyword"])

        data_kompleks = data_kompleks.filter(
            Q(cluster__icontains=search_keyword) | Q(nomor=search_keyword)
        )

    data = serializers.serialize("json", data_kompleks)
    return JsonResponse({"data": json.loads(data)})
