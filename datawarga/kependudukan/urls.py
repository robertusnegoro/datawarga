from django.urls import path, re_path
from . import utility, kompleks, warga, iuran, iuran_public
from django.conf import settings

app_name = "kependudukan"


urlpatterns = [
    path("", warga.index, name="index"),
    path("warga/form-warga/<int:idwarga>", warga.formWarga, name="formWarga"),
    path(
        "warga/form-warga/<int:idwarga>/<int:idkompleks>",
        warga.formWarga,
        name="formWargaRumah",
    ),
    path(
        "warga/delete-form-warga/<int:idwarga>",
        warga.deleteFormWarga,
        name="deleteformWarga",
    ),
    path("warga/form-warga-simpan", warga.formWargaSimpan, name="formWargaSimpan"),
    path("warga/list-warga-view", warga.WargaListView.as_view(), name="listWargaView"),
    path("warga/test-view", warga.testView, name="testView"),
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
    path(
        "warga/form-iuran-bulanan/<int:idkompleks>",
        iuran.form_iuran_bulanan,
        name="formIuranBulanan",
    ),
    path(
        "warga/form-iuran-bulanan/<int:idkompleks>/<int:year>",
        iuran.form_iuran_bulanan,
        name="formIuranBulananYear",
    ),
    path(
        "warga/form-iuran-bulanan/<int:idkompleks>/<int:year>/<int:idtransaksi>",
        iuran.form_iuran_bulanan,
        name="formIuranBulananYearTrx",
    ),
    path(
        "warga/form-iuran-bulanan-save",
        iuran.form_iuran_bulanan_save,
        name="formIuranBulananSave",
    ),
    path(
        "warga/list-iuran-bulanan-json/<int:idkompleks>",
        iuran.list_iuran_kompleks_tahun_json,
        name="listIuranBulananJson",
    ),
    path(
        "warga/list-iuran-bulanan-json/<int:idkompleks>/<int:year>",
        iuran.list_iuran_kompleks_tahun_json,
        name="listIuranBulananJsonYear",
    ),
    path(
        "warga/delete-iuran-bulanan/<int:idtransaksi>",
        iuran.delete_iuran_bulanan,
        name="deleteIuranBulanan",
    ),
    path("public/dashboard/<str:page>", utility.dashboard_public, name="publicDasboard"),
    path("public/iuran", iuran_public.form_iuran_bulanan_display, name="publicIuran"),
]

if settings.WG_ENV == "dev":
    urlpatterns.append(path("generate/<int:count>", utility.generate_data_warga))
