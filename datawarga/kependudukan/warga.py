from .forms import WargaForm, GenerateKompleksForm
from .models import Warga, Kompleks, WargaPermissionGroup, UserPermission
from datetime import datetime, timedelta
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core import serializers
from django.db.models import Q
from django.http import HttpResponse, Http404, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.utils.timezone import now
from django.views.generic import ListView
from django.views.static import serve
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
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
        context["daftar_cluster"] = list_cluster
        if "message" in self.request.GET:
            context["message"] = self.request.GET["message"]
        if "cluster" in self.request.GET and str(self.request.GET["cluster"]) != "all":
            context["cluster"] = str(self.request.GET["cluster"])
        if "search" in self.request.GET:
            context["search"] = str(self.request.GET["search"])
        return context

    def get_queryset(self):
        queryset = super().get_queryset()
        current_permission_group = UserPermission.objects.get(user=self.request.user)
        logger.info(current_permission_group.permission_group)

        if str(current_permission_group.permission_group).lower() != "all":
            queryset = queryset.filter(
                kompleks__permission_group=current_permission_group.permission_group.id
            )

        if "search" in self.request.GET:
            search_keyword = str(self.request.GET["search"])

            if "/" in search_keyword:
                split_keyword = search_keyword.split("/")
                queryset = queryset.filter(
                    kompleks__blok__icontains=split_keyword[0].strip(),
                    kompleks__nomor=split_keyword[1].strip(),
                )
            else:
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
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    dataWarga = Warga.objects.all().order_by("kompleks__blok", "kompleks__nomor")
    report_data = {"filter": {}}
    if request.POST:
        file_type = str(request.POST["file_type"])
        cluster = str(request.POST["cluster"])
        rukuntangga = str(request.POST["rt"])
        usia = str(request.POST["usia"])
        if cluster != "all":
            dataWarga = dataWarga.filter(kompleks__cluster=cluster)
            report_data["filter"]["cluster"] = cluster
        if len(rukuntangga) > 0:
            dataWarga = dataWarga.filter(kompleks__rt=rukuntangga)
            report_data["filter"]["rt"] = rukuntangga
        if "kepala_keluarga" in request.POST:
            dataWarga = dataWarga.filter(kepala_keluarga=True)
        today = now().date()
        if usia == "lansia":
            age_delta = 55 * 365
            age_date = today - timedelta(days=age_delta)
            dataWarga = dataWarga.filter(tanggal_lahir__lte=age_date)
        elif usia == "balita":
            age_delta = 5 * 365
            age_date = today - timedelta(days=age_delta)
            dataWarga = dataWarga.filter(tanggal_lahir__gte=age_date)

    report_data["data"] = dataWarga
    report_data["rw"] = settings.RUKUNWARGA
    report_data["alamat"] = settings.ALAMAT
    report_data["kelurahan"] = settings.KELURAHAN
    report_data["kecamatan"] = settings.KECAMATAN
    report_data["kota"] = settings.KOTA
    report_data["provinsi"] = settings.PROVINSI
    if file_type == "pdf":
        response = HttpResponse(content_type="application/pdf")
        response["Content-Disposition"] = "inline; filename=daftar-warga.pdf"
        html = render_to_string("daftar-warga-pdf-print.html", report_data)
        font_config = FontConfiguration()
        HTML(string=html).write_pdf(response, font_config=font_config)
        return response
    else:
        service = build(
            "sheets", "v4", credentials=settings.GOOGLE_SHEETS_SERVICE_ACCOUNT
        )

        spreadsheet = (
            service.spreadsheets()
            .create(body={"properties": {"title": f"Data Warga - {timestamp}"}})
            .execute()
        )

        # Retrieve the ID of the newly created spreadsheet
        spreadsheet_id = spreadsheet["spreadsheetId"]

        # Prepare the data to be written to the spreadsheet
        data = [
            [
                "Nama",
                "NIK",
                "KK",
                "Blok",
                "No Rumah",
                "RT",
                "RW",
                "Tempat Lahir",
                "Tanggal Lahir",
                "HP",
                "Jenis Kelamin",
                "Status Tinggal",
                "Status",
                "Agama",
                "Pekerjaan",
            ]
        ]

        for record in dataWarga:
            data.append(
                [
                    record.nama_lengkap,
                    record.nik,
                    record.no_kk,
                    record.kompleks.blok,
                    record.kompleks.nomor,
                    record.kompleks.rt,
                    record.kompleks.rw,
                    record.tempat_lahir,
                    str(record.tanggal_lahir),
                    record.no_hp,
                    record.jenis_kelamin,
                    record.status_tinggal,
                    record.status,
                    record.agama,
                    record.pekerjaan,
                ]
            )

        # Write the data to the spreadsheet
        service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range="Sheet1!A1",
            valueInputOption="RAW",
            body={"values": data},
        ).execute()

        if settings.GOOGLE_DRIVE_USER is not None:
            try:
                drive_service = build(
                    "drive", "v3", credentials=settings.GOOGLE_SHEETS_SERVICE_ACCOUNT
                )
                user_permission = {
                    "type": "user",
                    "role": "writer",
                    "emailAddress": settings.GOOGLE_DRIVE_USER,
                }
                drive_service.permissions().create(
                    fileId=spreadsheet_id, body=user_permission, fields="id"
                ).execute()
            except HttpError as e:
                logger.error(e)

        # Construct the URL to the generated Google Sheets document
        spreadsheet_url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}"

        return render(request, "sheet-link.html", {"spreadsheet_url": spreadsheet_url})


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


@login_required
def set_kepala_keluarga(request, idwarga):
    warga_record = get_object_or_404(Warga, pk=idwarga)
    warga_serumah = Warga.objects.filter(kompleks=warga_record.kompleks)
    for warga in warga_serumah:
        warga.kepala_keluarga = False
        warga.save()

    warga_record.kepala_keluarga = True
    warga_record.save()

    base_url = reverse(
        "kependudukan:detailKompleks", kwargs={"idkompleks": warga_record.kompleks.id}
    )
    payload = urlencode({"message": "data saved!"})
    url_redir = "{}?{}".format(base_url, payload)
    return redirect(url_redir)
