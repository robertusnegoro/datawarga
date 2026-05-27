from kependudukan.forms import WargaForm
from kependudukan.models import (
    Warga,
    Kompleks,
    UserPermission,
    Kendaraan,
    Surat,
    TransaksiIuranBulanan,
    WargaUpdateRequest,
)
from django.core.exceptions import PermissionDenied
from datetime import datetime, timedelta
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_POST
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
import uuid
from kependudukan.services.warga_service import assign_kepala_keluarga, process_ktp_scan
from kependudukan.selectors.warga_selector import (
    check_user_permission_for_kompleks,
    check_user_permission_for_warga,
    search_warga_queryset,
    get_anggota_keluarga,
    get_no_kk_for_kompleks,
)
from kependudukan.utils.auth_guards import admin_or_petugas_required

logger = logging.getLogger(__name__)


# Create your views here.
@login_required
def index(request):
    return redirect(reverse("kependudukan:dashboardWarga"))


@login_required
@admin_or_petugas_required
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
@admin_or_petugas_required
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
            messages.success(
                request,
                f"Data warga <strong>{warga.nama_lengkap}</strong> berhasil disimpan.",
            )
            return redirect(
                reverse("kependudukan:detailWarga", kwargs={"idwarga": warga.id})
            )
        else:
            logger.info(form.errors)
            return HttpResponse("form is not valid %s" % (form.errors))
    else:
        return Http404()


@method_decorator(login_required, name="dispatch")
@method_decorator(admin_or_petugas_required, name="dispatch")
class WargaListView(ListView):
    paginate_by = 50
    template_name = "list_warga_view.html"
    queryset = Warga.objects.exclude(
        status_tinggal__in=["PINDAH", "MENINGGAL"]
    ).order_by("kompleks__blok", "kompleks__nomor")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        list_cluster = Kompleks.objects.order_by().values("cluster").distinct()
        context["daftar_cluster"] = list_cluster
        if "message" in self.request.GET:
            context["message"] = self.request.GET["message"]
        context["cluster"] = self.request.GET.get("cluster", "all")
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
            queryset = search_warga_queryset(queryset, self.request.GET["search"])
        if "cluster" in self.request.GET and str(self.request.GET["cluster"]) != "all":
            cluster = str(self.request.GET["cluster"])
            queryset = queryset.filter(kompleks__cluster__icontains=cluster)

        return queryset


@method_decorator(login_required, name="dispatch")
@method_decorator(admin_or_petugas_required, name="dispatch")
class KepalaKeluargaListView(ListView):
    paginate_by = 50
    template_name = "daftar_kepala_keluarga.html"
    queryset = (
        Warga.objects.filter(kepala_keluarga=True)
        .exclude(status_tinggal__in=["PINDAH", "MENINGGAL"])
        .order_by("kompleks__blok", "kompleks__nomor")
    )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        list_cluster = Kompleks.objects.order_by().values("cluster").distinct()
        context["daftar_cluster"] = list_cluster
        if "message" in self.request.GET:
            context["message"] = self.request.GET["message"]
        context["cluster"] = self.request.GET.get("cluster", "all")
        if "search" in self.request.GET:
            context["search"] = str(self.request.GET["search"])
        return context

    def get_queryset(self):
        queryset = super().get_queryset()
        try:
            current_permission_group = UserPermission.objects.get(
                user=self.request.user
            )
            if str(current_permission_group.permission_group).lower() != "all":
                queryset = queryset.filter(
                    kompleks__permission_group=current_permission_group.permission_group.id
                )
        except UserPermission.DoesNotExist:
            pass

        if "search" in self.request.GET:
            queryset = search_warga_queryset(queryset, self.request.GET["search"])
        if "cluster" in self.request.GET and str(self.request.GET["cluster"]) != "all":
            cluster = str(self.request.GET["cluster"])
            queryset = queryset.filter(kompleks__cluster__icontains=cluster)

        return queryset


@login_required
@admin_or_petugas_required
def detail_anggota_keluarga_snippet(request, idkompleks):
    kompleks = get_object_or_404(Kompleks, pk=idkompleks)

    if not check_user_permission_for_kompleks(request.user, kompleks):
        return HttpResponse("Forbidden", status=403)

    data_warga = get_anggota_keluarga(kompleks.id)
    no_kk = get_no_kk_for_kompleks(kompleks.id)

    context = {
        "kompleks": kompleks,
        "anggota": data_warga,
        "no_kk": no_kk,
        "MEDIA_URL": settings.MEDIA_URL,
    }
    return render(request, "anggota_keluarga_snippet.html", context)


@login_required
@admin_or_petugas_required
def deleteFormWarga(request, idwarga=0):
    warga_record = get_object_or_404(Warga, pk=idwarga)
    next_url = request.GET.get("next")
    if request.POST:
        warga_record.delete()
        logger.info(
            "Deleting data warga with id : %s , name : %s"
            % (idwarga, warga_record.nama_lengkap)
        )
        base_url = reverse("kependudukan:listWargaView")
        if next_url == "arsip":
            base_url = reverse("kependudukan:arsipWargaView")
        messages.success(
            request,
            f"Data warga <strong>{warga_record.nama_lengkap}</strong> berhasil dihapus.",
        )
        return redirect(base_url)
    else:
        return render(
            request=request,
            template_name="delete_form_warga.html",
            context={"idwarga": idwarga, "warga": warga_record, "next": next_url},
        )


@method_decorator(login_required, name="dispatch")
@method_decorator(admin_or_petugas_required, name="dispatch")
class ArsipWargaListView(ListView):
    paginate_by = 50
    template_name = "arsip_warga.html"
    queryset = Warga.objects.filter(
        status_tinggal__in=["PINDAH", "MENINGGAL"]
    ).order_by("kompleks__blok", "kompleks__nomor")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        list_cluster = Kompleks.objects.order_by().values("cluster").distinct()
        context["daftar_cluster"] = list_cluster
        if "message" in self.request.GET:
            context["message"] = self.request.GET["message"]
        context["cluster"] = self.request.GET.get("cluster", "all")
        if "search" in self.request.GET:
            context["search"] = str(self.request.GET["search"])
        return context

    def get_queryset(self):
        queryset = super().get_queryset()
        try:
            current_permission_group = UserPermission.objects.get(
                user=self.request.user
            )
            if str(current_permission_group.permission_group).lower() != "all":
                queryset = queryset.filter(
                    kompleks__permission_group=current_permission_group.permission_group.id
                )
        except UserPermission.DoesNotExist:
            pass

        if "search" in self.request.GET:
            queryset = search_warga_queryset(queryset, self.request.GET["search"])
        if "cluster" in self.request.GET and str(self.request.GET["cluster"]) != "all":
            cluster = str(self.request.GET["cluster"])
            queryset = queryset.filter(kompleks__cluster__icontains=cluster)

        return queryset


def testView(request):
    context = {"legend": ["One", "Two", "Three", "Four", "Five"]}
    return render(request=request, template_name="test.html", context=context)


@login_required
@admin_or_petugas_required
def listWargaReportForm(request):
    list_cluster = Kompleks.objects.order_by().values("cluster").distinct()
    context = {"list_cluster": list_cluster, "status_tinggal": Warga.STATUS_TINGGAL}
    return render(
        request=request, template_name="form_list_warga_report.html", context=context
    )


@login_required
@admin_or_petugas_required
def pdfWargaReport(request):
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    dataWarga = Warga.objects.all().order_by("kompleks__blok", "kompleks__nomor")
    report_data = {"filter": {}}
    if request.POST:
        file_type = str(request.POST["file_type"])
        cluster = str(request.POST["cluster"])
        status_tinggal = str(request.POST["status_tinggal"]).upper()
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
        if status_tinggal != "ALL":
            dataWarga = dataWarga.filter(status_tinggal=status_tinggal)
            report_data["filter"]["status_tinggal"] = status_tinggal

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
        if settings.GOOGLE_SHEETS_SERVICE_ACCOUNT is None:
            return HttpResponse(
                "Google Sheets export is not configured. Set GOOGLE_CRED_PATH to the path of the service account JSON file inside the container (and mount that file when running Docker).",
                status=503,
                content_type="text/plain",
            )
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
            kompleks = record.kompleks
            data.append(
                [
                    record.nama_lengkap.upper(),
                    record.nik,
                    record.no_kk,
                    kompleks.blok if kompleks else "",
                    kompleks.nomor if kompleks else "",
                    kompleks.rt if kompleks else "",
                    kompleks.rw if kompleks else "",
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
@admin_or_petugas_required
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
@admin_or_petugas_required
def set_kepala_keluarga(request, idwarga):
    warga_record = assign_kepala_keluarga(idwarga)

    base_url = reverse(
        "kependudukan:detailKompleks", kwargs={"idkompleks": warga_record.kompleks.id}
    )
    payload = urlencode({"message": "data saved!"})
    url_redir = "{}?{}".format(base_url, payload)
    return redirect(url_redir)


@login_required
@admin_or_petugas_required
def detailWarga(request, idwarga):
    warga = get_object_or_404(Warga, pk=idwarga)

    if not check_user_permission_for_warga(request.user, warga):
        return HttpResponse("Forbidden", status=403)

    # Fetch other household members (serumah)
    anggota_keluarga = []
    if warga.kompleks:
        anggota_keluarga = get_anggota_keluarga(
            warga.kompleks.id, exclude_warga_id=warga.id
        )

    # Fetch recent transactions for this complex
    transaksi = []
    if warga.kompleks:
        from kependudukan.models import TransaksiIuranBulanan

        transaksi = TransaksiIuranBulanan.objects.filter(
            kompleks=warga.kompleks
        ).order_by("-periode_tahun", "-periode_bulan")[:5]

    umur = None
    if warga.tanggal_lahir:
        today = datetime.now().date()
        birth = warga.tanggal_lahir
        umur = (
            today.year
            - birth.year
            - ((today.month, today.day) < (birth.month, birth.day))
        )

    kendaraan_list = Kendaraan.objects.filter(pemilik=warga)

    context = {
        "warga": warga,
        "anggota_keluarga": anggota_keluarga,
        "transaksi": transaksi,
        "umur": umur,
        "kendaraan_list": kendaraan_list,
        "MEDIA_URL": settings.MEDIA_URL,
        "new_user_invitation_token": request.session.pop(
            "new_user_invitation_token", None
        ),
        "invitation_template": (
            "Halo {name},\n\n"
            "Anda diundang untuk mengaktifkan akun portal Warga di sistem DataWarga. "
            "Silakan klik tautan di bawah ini untuk mengatur kata sandi Anda dan mengaktifkan akun Anda:\n\n"
            "{link}\n\n"
            "Tautan ini berlaku sampai {expires_at}.\n\n"
            "Salam,\n"
            "Pengurus RT/RW"
        ),
    }
    return render(request, "detail_warga.html", context)


@login_required
@admin_or_petugas_required
def pdfDetailWarga(request, idwarga):
    warga = get_object_or_404(Warga, pk=idwarga)

    if not check_user_permission_for_warga(request.user, warga):
        return HttpResponse("Forbidden", status=403)

    # Fetch other household members (serumah)
    anggota_keluarga = []
    if warga.kompleks:
        anggota_keluarga = get_anggota_keluarga(
            warga.kompleks.id, exclude_warga_id=warga.id
        )

    # Fetch recent transactions for this complex
    transaksi = []
    if warga.kompleks:
        from kependudukan.models import TransaksiIuranBulanan

        transaksi = TransaksiIuranBulanan.objects.filter(
            kompleks=warga.kompleks
        ).order_by("-periode_tahun", "-periode_bulan")[:5]

    umur = None
    if warga.tanggal_lahir:
        today = datetime.now().date()
        birth = warga.tanggal_lahir
        umur = (
            today.year
            - birth.year
            - ((today.month, today.day) < (birth.month, birth.day))
        )

    kendaraan_list = Kendaraan.objects.filter(pemilik=warga)

    # For PDF generation, we should pass standard config variables too
    context = {
        "warga": warga,
        "anggota_keluarga": anggota_keluarga,
        "transaksi": transaksi,
        "umur": umur,
        "kendaraan_list": kendaraan_list,
        "MEDIA_URL": settings.MEDIA_URL,
        "rw": settings.RUKUNWARGA,
        "rt": warga.kompleks.rt if warga.kompleks else "-",
        "alamat": settings.ALAMAT,
        "kelurahan": settings.KELURAHAN,
        "kecamatan": settings.KECAMATAN,
        "kota": settings.KOTA,
        "provinsi": settings.PROVINSI,
    }

    # Generate PDF via WeasyPrint
    response = HttpResponse(content_type="application/pdf")
    safe_name = warga.nama_lengkap.replace(" ", "_").lower()
    response["Content-Disposition"] = "inline; filename=profil-{}.pdf".format(safe_name)

    html = render_to_string("detail_warga_pdf.html", context, request=request)
    font_config = FontConfiguration()
    HTML(string=html, base_url=request.build_absolute_uri("/")).write_pdf(
        response, font_config=font_config
    )
    return response


@login_required
@require_POST
@admin_or_petugas_required
def scan_ktp_ajax(request):

    correlation_id = str(uuid.uuid4())
    logger.info(
        f"[SCAN_KTP_REQUEST] [CorrelationID: {correlation_id}] User: {request.user.username}"
    )

    image_bytes = None
    filename = ""

    if "ktp_image" in request.FILES:
        ktp_file = request.FILES["ktp_image"]
        filename = ktp_file.name
        image_bytes = ktp_file.read()
        logger.info(
            f"[SCAN_KTP_IMAGE] [CorrelationID: {correlation_id}] Uploaded file: {filename}, size: {len(image_bytes)} bytes"
        )
    elif "idwarga" in request.POST and request.POST["idwarga"]:
        try:
            idwarga = int(request.POST["idwarga"])
            warga_record = Warga.objects.get(pk=idwarga)
            if warga_record.ktp_image_path:
                filename = warga_record.ktp_image_path.name
                warga_record.ktp_image_path.open("rb")
                image_bytes = warga_record.ktp_image_path.read()
                warga_record.ktp_image_path.close()
                logger.info(
                    f"[SCAN_KTP_IMAGE] [CorrelationID: {correlation_id}] Loaded existing image for warga {idwarga}: {filename}, size: {len(image_bytes)} bytes"
                )
            else:
                logger.warning(
                    f"[SCAN_KTP_IMAGE] [CorrelationID: {correlation_id}] Resident {idwarga} has no uploaded KTP image."
                )
        except Warga.DoesNotExist:
            logger.error(
                f"[SCAN_KTP_IMAGE] [CorrelationID: {correlation_id}] Resident with ID {request.POST.get('idwarga')} not found."
            )
            return JsonResponse(
                {"success": False, "message": "Data warga tidak ditemukan."}, status=404
            )
        except Exception as e:
            logger.error(
                f"[SCAN_KTP_IMAGE] [CorrelationID: {correlation_id}] Error reading citizen KTP image: {str(e)}",
                exc_info=True,
            )
            return JsonResponse(
                {"success": False, "message": f"Gagal membaca file KTP: {str(e)}"},
                status=500,
            )

    if not image_bytes:
        logger.warning(
            f"[SCAN_KTP_IMAGE] [CorrelationID: {correlation_id}] No KTP file uploaded and no valid resident ID with KTP provided."
        )
        return JsonResponse(
            {
                "success": False,
                "message": "Pilih file foto KTP terlebih dahulu atau simpan data warga dengan foto KTP.",
            },
            status=400,
        )

    success, msg, extracted_data, quota_warning, quota_message = process_ktp_scan(
        image_bytes, correlation_id
    )
    if success:
        return JsonResponse(
            {
                "success": True,
                "data": extracted_data,
                "message": msg,
                "quota_warning": quota_warning,
                "quota_message": quota_message,
            }
        )
    else:
        return JsonResponse(
            {"success": False, "message": msg},
            status=500,
        )


@login_required
def warga_dashboard(request):
    """
    Renders a premium dashboard customized for citizens (warga).
    """
    try:
        warga = request.user.warga
    except AttributeError:
        raise PermissionDenied("Hanya warga terdaftar yang dapat mengakses portal ini.")

    if warga is None:
        raise PermissionDenied("Hanya warga terdaftar yang dapat mengakses portal ini.")

    # Retrieve family members in the same complex
    anggota_keluarga = []
    if warga.kompleks:
        anggota_keluarga = get_anggota_keluarga(
            warga.kompleks.id, exclude_warga_id=warga.id
        )

    # Retrieve registered vehicles (including pending registrations)
    kendaraan_list = Kendaraan.objects.filter(pemilik=warga).order_by("-id")

    # Retrieve document requests (Surat)
    surat_list = Surat.objects.filter(warga=warga).order_by("-tanggal_surat")

    # Retrieve dues payments for their complex
    transaksi = []
    if warga.kompleks:
        transaksi = TransaksiIuranBulanan.objects.filter(
            kompleks=warga.kompleks
        ).order_by("-periode_tahun", "-periode_bulan")

    # Retrieve pending profile updates
    from django.db.models import Q
    update_requests = WargaUpdateRequest.objects.filter(
        Q(warga=warga) | Q(requested_by=warga)
    ).distinct().order_by("-created_at")

    context = {
        "warga": warga,
        "anggota_keluarga": anggota_keluarga,
        "kendaraan_list": kendaraan_list,
        "surat_list": surat_list,
        "transaksi": transaksi,
        "update_requests": update_requests,
        "MEDIA_URL": settings.MEDIA_URL,
        "religions": Warga.RELIGIONS,
        "status_kawin": Warga.STATUS_KAWIN,
        "status_tinggal": Warga.STATUS_TINGGAL,
        "pekerjaan_choices": Warga.PEKERJAAN,
        "jenis_kelamin_choices": Warga.JENIS_KELAMIN,
        "status_keluarga_choices": Warga.STATUS_KELUARGA,
        "iuran_bulanan": settings.IURAN_BULANAN,
    }
    return render(request, "warga_dashboard.html", context)


@login_required
def warga_request_surat(request):
    """
    Post handler for warga to request a document (Surat).
    """
    if request.method == "POST":
        try:
            warga = request.user.warga
        except AttributeError:
            raise PermissionDenied()

        if warga is None:
            raise PermissionDenied()

        jenis_surat = request.POST.get("jenis_surat")
        keperluan = request.POST.get("keperluan", "").strip()

        if not jenis_surat or not keperluan:
            messages.error(request, "Jenis surat dan keperluan harus diisi.")
            return redirect("kependudukan:warga_dashboard")

        Surat.objects.create(
            warga=warga, jenis_surat=jenis_surat, keperluan=keperluan, status="PENDING"
        )
        messages.success(
            request,
            "Permohonan surat berhasil diajukan dan sedang menunggu persetujuan.",
        )
    return redirect("kependudukan:warga_dashboard")


@login_required
def warga_register_kendaraan(request):
    """
    Post handler for warga to register a vehicle.
    """
    if request.method == "POST":
        try:
            warga = request.user.warga
        except AttributeError:
            raise PermissionDenied()

        if warga is None:
            raise PermissionDenied()

        jenis_kendaraan = request.POST.get("jenis_kendaraan", "MOBIL")
        merk = request.POST.get("merk", "").strip()
        tipe = request.POST.get("tipe", "").strip()
        plat_nomor = request.POST.get("plat_nomor", "").strip().upper()
        keterangan = request.POST.get("keterangan", "").strip()

        if not plat_nomor:
            messages.error(request, "Plat nomor kendaraan harus diisi.")
            return redirect("kependudukan:warga_dashboard")

        # User-friendly check for unique license plate constraint
        if Kendaraan.objects.filter(plat_nomor=plat_nomor).exists():
            messages.error(request, f"Plat nomor {plat_nomor} sudah terdaftar.")
            return redirect("kependudukan:warga_dashboard")

        Kendaraan.objects.create(
            pemilik=warga,
            jenis_kendaraan=jenis_kendaraan,
            merk=merk,
            tipe=tipe,
            plat_nomor=plat_nomor,
            keterangan=keterangan,
            status="PENDING",
        )
        messages.success(
            request,
            "Registrasi kendaraan berhasil diajukan dan sedang menunggu persetujuan.",
        )
    return redirect("kependudukan:warga_dashboard")


@login_required
def warga_upload_iuran(request):
    """
    Post handler for warga to submit dues payment proof.
    """
    if request.method == "POST":
        try:
            warga = request.user.warga
        except AttributeError:
            raise PermissionDenied()

        if warga is None:
            raise PermissionDenied()

        if not warga.kompleks:
            messages.error(
                request,
                "Akun Anda belum terasosiasi dengan nomor rumah/kompleks. Hubungi admin.",
            )
            return redirect("kependudukan:warga_dashboard")

        try:
            periode_bulan = int(request.POST.get("periode_bulan", 0))
            periode_tahun = int(request.POST.get("periode_tahun", 0))
            total_bayar_str = request.POST.get("total_bayar")
            if total_bayar_str is not None and total_bayar_str.strip() != "":
                total_bayar = int(total_bayar_str)
            else:
                total_bayar = settings.IURAN_BULANAN
        except (TypeError, ValueError):
            messages.error(
                request, "Input periode bulan, tahun, atau total bayar tidak valid."
            )
            return redirect("kependudukan:warga_dashboard")

        bukti_bayar = request.FILES.get("bukti_bayar")
        keterangan = request.POST.get("keterangan", "").strip()

        if not periode_bulan or not periode_tahun or not bukti_bayar:
            messages.error(
                request, "Bulan, tahun, dan file bukti pembayaran harus dilampirkan."
            )
            return redirect("kependudukan:warga_dashboard")

        # Exclude rejected transactions when checking duplicate attempts
        existing = (
            TransaksiIuranBulanan.objects.filter(
                kompleks=warga.kompleks,
                periode_bulan=periode_bulan,
                periode_tahun=periode_tahun,
            )
            .exclude(status="REJECTED")
            .exists()
        )

        if existing:
            messages.error(
                request,
                f"Pembayaran untuk periode bulan {periode_bulan} tahun {periode_tahun} sudah tercatat atau sedang menunggu persetujuan.",
            )
            return redirect("kependudukan:warga_dashboard")

        TransaksiIuranBulanan.objects.create(
            kompleks=warga.kompleks,
            periode_bulan=periode_bulan,
            periode_tahun=periode_tahun,
            total_bayar=total_bayar,
            bukti_bayar=bukti_bayar,
            keterangan=keterangan,
            status="PENDING",
        )
        messages.success(
            request,
            "Bukti pembayaran iuran berhasil diunggah dan sedang menunggu persetujuan.",
        )
    return redirect("kependudukan:warga_dashboard")


@login_required
def warga_submit_update(request):
    """
    Post handler for warga to submit a profile update request.
    """
    if request.method == "POST":
        try:
            warga = request.user.warga
        except AttributeError:
            raise PermissionDenied()

        if warga is None:
            raise PermissionDenied()

        target_warga_id = request.POST.get("target_warga_id")
        target_warga = None
        is_new_warga = False
        
        if target_warga_id == "NEW":
            is_new_warga = True
        elif target_warga_id:
            try:
                target_warga = Warga.objects.get(pk=target_warga_id)
                if not (target_warga == warga or (warga.kompleks and target_warga.kompleks == warga.kompleks)):
                    messages.error(request, "Target warga tidak valid atau tidak berada dalam satu rumah.")
                    return redirect("kependudukan:warga_dashboard")
            except Warga.DoesNotExist:
                messages.error(request, "Target warga tidak ditemukan.")
                return redirect("kependudukan:warga_dashboard")
        else:
            target_warga = warga

        updatable_fields = [
            "nama_lengkap",
            "nik",
            "no_hp",
            "no_kk",
            "pekerjaan",
            "agama",
            "status",
            "tanggal_lahir",
            "tempat_lahir",
            "jenis_kelamin",
            "kewarganegaraan",
            "status_tinggal",
            "status_keluarga",
            "alamat_ktp",
        ]
        changes = {}
        for field in updatable_fields:
            val = request.POST.get(field)
            if val is not None:
                changes[field] = val.strip()

        files = {}
        if "foto_path" in request.FILES:
            files["foto_path"] = request.FILES["foto_path"]
        if "ktp_image_path" in request.FILES:
            files["ktp_image_path"] = request.FILES["ktp_image_path"]

        from kependudukan.services.warga_service import submit_warga_update_request

        submit_warga_update_request(
            warga=target_warga,
            fields_data=changes,
            files=files,
            requested_by=warga,
            is_new_warga=is_new_warga,
            kompleks=warga.kompleks
        )
        messages.success(
            request,
            "Perubahan data diri berhasil diajukan dan sedang menunggu persetujuan.",
        )
    return redirect("kependudukan:warga_dashboard")
