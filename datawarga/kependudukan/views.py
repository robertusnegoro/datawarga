from .forms import WargaForm
from .models import Warga
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import HttpResponse, Http404, JsonResponse, FileResponse
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
import random

logger = logging.getLogger(__name__)

# Create your views here.
@login_required
def index(request):
    return render(request=request, template_name="index.html")


@login_required
def formWarga(request, idwarga=0):
    if idwarga == 0:
        form = WargaForm()
    else:
        warga_record = get_object_or_404(Warga, pk=idwarga)
        form = WargaForm(instance=warga_record)
    logger.info("Form warga empty loaded")
    return render(
        request=request,
        template_name="form_warga.html",
        context={"form": form, "idwarga": int(idwarga)},
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
    queryset = Warga.objects.order_by("-id")

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
                Q(nama_lengkap__icontains=search_keyword)
                | Q(nik__icontains=search_keyword)
            )
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
    return render(request=request, template_name="test.html")


@login_required
def listWargaReport(request):
    dataWarga = Warga.objects.all()
    report_data = {"data": dataWarga}
    report_data["alamat"] = settings.ALAMAT
    report_data["rt"] = settings.RUKUNTANGGA
    report_data["rw"] = settings.RUKUNWARGA
    report_data["kelurahan"] = settings.KELURAHAN
    report_data["kecamatan"] = settings.KECAMATAN
    report_data["kota"] = settings.KOTA
    report_data["provinsi"] = settings.PROVINSI
    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = "inline; filename=daftar-warga.pdf"
    html = render_to_string("daftar-warga-pdf.html", report_data)
    font_config = FontConfiguration()
    HTML(string=html).write_pdf(response, font_config=font_config)
    return response


@login_required
def protected_serve(request, path, document_root=None, show_indexes=False):
    return serve(request, path, document_root, show_indexes)


@login_required
def generate_data_warga(request):
    count = 250
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
