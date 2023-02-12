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

# Create your views here.
@login_required
def index(request):
    return redirect(reverse("kependudukan:dashboardWarga"))


@login_required
def formWarga(request, idwarga=0, idkompleks=0):
    context = {"idkompleks": int(idkompleks)}
    if idkompleks > 0:
        if idwarga > 0:
            url_redir = reverse(
                "kependudukan:formWargaRumah",
                kwargs={"idwarga": 0, "idkompleks": idkompleks},
            )
            return redirect(url_redir)
        data_kompleks = get_object_or_404(Kompleks, pk=idkompleks)
        context["data_kompleks"] = data_kompleks

    if idwarga == 0:
        form = WargaForm()
    else:
        warga_record = get_object_or_404(Warga, pk=idwarga)
        context["datawarga"] = warga_record
        form = WargaForm(instance=warga_record)

    context["form"] = form
    context["idwarga"] = int(idwarga)

    logger.info("Form warga empty loaded")
    return render(
        request=request,
        template_name="form_warga.html",
        context=context,
    )


@login_required
def formWargaSimpan(request):
    if request.POST:
        if "idwarga" in request.POST:
            idwarga = int(request.POST["idwarga"])
            warga_record = get_object_or_404(Warga, pk=idwarga)
            logger.info("update mode")
            form = WargaForm(request.POST, request.FILES, instance=warga_record)
        else:
            logger.info("insert mode")
            form = WargaForm(request.POST, request.FILES)
        if form.is_valid():
            logger.info("Form warga is valid")
            warga = form.save()
            base_url = reverse("kependudukan:listWargaView")
            payload = urlencode({"message": "data saved!"})
            url_redir = "{}?{}".format(base_url, payload)

            if "idkompleks" in request.POST:
                base_url = reverse(
                    "kependudukan:detailKompleks",
                    kwargs={"idkompleks": int(request.POST["idkompleks"])},
                )
                payload = urlencode({"message": "data saved!"})
                url_redir = "{}?{}".format(base_url, payload)

            return redirect(url_redir)
        else:
            logger.info(form.errors)
            return HttpResponse("form is not valid %s" % (form.errors))
    else:
        return Http404()


@method_decorator(login_required, name="dispatch")
class WargaListView(ListView):
    paginate_by = 50
    template_name = "list_warga_view.html"
    queryset = Warga.objects.order_by("kompleks__blok", "kompleks__nomor")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        list_cluster = Kompleks.objects.order_by().values("cluster").distinct()
        context['daftar_cluster'] = list_cluster
        if "message" in self.request.GET:
            context["message"] = self.request.GET["message"]
        if "cluster" in self.request.GET and str(self.request.GET["cluster"]) != "all":
            context["cluster"] = str(self.request.GET["cluster"])
        return context

    def get_queryset(self):
        queryset = super().get_queryset()
        if "search" in self.request.GET:
            search_keyword = str(self.request.GET["search"])

            queryset = queryset.filter(
                Q(nama_lengkap__icontains=search_keyword)
                | Q(nik__icontains=search_keyword)
            )
        if "cluster" in self.request.GET and str(self.request.GET["cluster"]) != "all":
            cluster = str(self.request.GET["cluster"])
            queryset = queryset.filter(kompleks__cluster__icontains=cluster)
        return queryset


@login_required
def deleteFormWarga(request, idwarga=0):
    warga_record = get_object_or_404(Warga, pk=idwarga)
    if request.POST:
        warga_record.delete()
        logger.info(
            "Deleting data warga with id : %s , name : %s"
            % (idwarga, warga_record.nama_lengkap)
        )
        base_url = reverse("kependudukan:listWargaView")
        payload = urlencode(
            {"message": "data %s was deleted!" % (warga_record.nama_lengkap)}
        )
        url_redir = "{}?{}".format(base_url, payload)
        return redirect(url_redir)
    else:
        return render(
            request=request,
            template_name="delete_form_warga.html",
            context={"idwarga": idwarga, "warga": warga_record},
        )


def testView(request):
    context = {"legend": ["One", "Two", "Three", "Four", "Five"]}
    return render(request=request, template_name="test.html", context=context)


@login_required
def listWargaReportForm(request):
    list_cluster = Kompleks.objects.order_by().values("cluster").distinct()
    context = {"list_cluster": list_cluster}
    return render(
        request=request, template_name="form_list_warga_report.html", context=context
    )


@login_required
def pdfWargaReport(request):
    dataWarga = Warga.objects.all().order_by("kompleks__blok", "kompleks__nomor")
    report_data = {"filter": {}}
    if request.POST:
        cluster = str(request.POST["cluster"])
        rukuntangga = str(request.POST["rt"])
        if cluster != "all":
            dataWarga = dataWarga.filter(kompleks__cluster=cluster)
            report_data["filter"]["cluster"] = cluster
        if len(rukuntangga) > 0:
            dataWarga = dataWarga.filter(kompleks__rt=rukuntangga)
            report_data["filter"]["rt"] = rukuntangga
    report_data["data"] = dataWarga
    report_data["rw"] = settings.RUKUNWARGA
    report_data["alamat"] = settings.ALAMAT
    report_data["kelurahan"] = settings.KELURAHAN
    report_data["kecamatan"] = settings.KECAMATAN
    report_data["kota"] = settings.KOTA
    report_data["provinsi"] = settings.PROVINSI
    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = "inline; filename=daftar-warga.pdf"
    html = render_to_string("daftar-warga-pdf-print.html", report_data)
    font_config = FontConfiguration()
    HTML(string=html).write_pdf(response, font_config=font_config)
    return response


@login_required
def protected_serve(request, path, document_root=None, show_indexes=False):
    return serve(request, path, document_root, show_indexes)


@login_required
def list_warga_no_kompleks_json(request):
    data_warga = Warga.objects.filter(kompleks=None)
    if request.POST:
        search_keyword = str(request.POST["warga_search_keyword"])
        data_warga = data_warga.filter(
            Q(nama_lengkap__icontains=search_keyword) | Q(nik__icontains=search_keyword)
        )
    data = serializers.serialize("json", data_warga)
    return JsonResponse({"data": json.loads(data)})
