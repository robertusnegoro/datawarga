from django.urls import path, re_path
from . import utility, kompleks, warga
from django.conf import settings

app_name = "kependudukan"


urlpatterns = [
    path("", warga.index, name="index"),
    path("warga/form-warga/<int:idwarga>", warga.formWarga, name="formWarga"),
    path(
        "warga/delete-form-warga/<int:idwarga>",
        warga.deleteFormWarga,
        name="deleteformWarga",
    ),
    path("warga/form-warga-simpan", warga.formWargaSimpan, name="formWargaSimpan"),
    path("warga/list-warga-view", warga.WargaListView.as_view(), name="listWargaView"),
    path("warga/test-view", warga.testView, name="testView"),
    path("warga/data-warga-pdf", warga.listWargaReport, name="dataWargaPDF"),
    path("warga/form-warga-report", warga.listWargaReportForm, name="formWargaReport"),
    path("warga/data-warga-pdf-print", warga.pdfWargaReport, name="pdfWargaReport"),
    path("warga/dashboard-report", utility.dashboard_warga, name="dashboardWarga"),
    path("warga/form-kompleks", kompleks.kompleks_form, name="kompleksForm"),
    path(
        "warga/generate-kompleks-exec",
        kompleks.generate_kompleks,
        name="generateKompleks",
    ),
    path(
        "warga/list-kompleks-view",
        kompleks.KompleksListView.as_view(),
        name="listKompleksView",
    ),
    path("warga/delete-blok-form", kompleks.delete_blok_form, name="deleteBlokForm"),
    path(
        "warga/detail-kompleks/<int:idkompleks>",
        kompleks.detail_kompleks,
        name="detailKompleks",
    ),
    path("warga/warga-rumah/<int:idkompleks>", kompleks.warga_rumah, name="wargaRumah"),
    path(
        "warga/form-warga-rumah/<int:idkompleks>",
        kompleks.form_warga_rumah,
        name="formWargaRumah",
    ),
    path(
        "warga/form-delete-rumah/<int:idkompleks>",
        kompleks.delete_rumah_form,
        name="deleteRumahForm",
    ),
    path(
        "warga/utility/import-warga",
        utility.import_data_warga_form,
        name="utilImportWarga",
    ),
    path(
        "warga/utility/assign-warga-rumah",
        utility.assign_warga_rumah,
        name="utilAssignWargaRumah",
    ),
    path(
        "warga/list-warga-no-kompleks-json",
        warga.list_warga_no_kompleks_json,
        name="listWargaNoKompleksJson",
    ),
    path(
        "warga/list-kompleks-json", kompleks.list_kompleks_json, name="listKompleksJson"
    ),
    path(
        "warga/utility/assign-warga-rumah-exec",
        utility.assign_warga_rumah_exec,
        name="utilAssignWargaRumahExec",
    ),
    re_path(
        r"^%s(?P<path>.*)$" % settings.MEDIA_URL[1:],
        warga.protected_serve,
        {"document_root": settings.MEDIA_ROOT},
    ),
]

if settings.WG_ENV == "dev":
    urlpatterns.append(path("generate/<int:count>", utility.generate_data_warga))
