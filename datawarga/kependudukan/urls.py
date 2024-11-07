from django.urls import path, re_path, include
from . import utility, kompleks, warga, iuran, iuran_public, api_view
from django.conf import settings
from datetime import datetime
from rest_framework.routers import DefaultRouter
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

from drf_yasg.views import get_schema_view
from drf_yasg import openapi

app_name = "kependudukan"

router = DefaultRouter()
router.register(r"warga", api_view.wargaViewSet)

schema_view = get_schema_view(
    openapi.Info(
        title="Datawarga API",
        default_version="v1",
        description="Datawarga API Documentation",
        terms_of_service="https://www.google.com/policies/terms/",
        contact=openapi.Contact(email="dopydino@protonmail.com"),
        license=openapi.License(name="BSD License"),
    ),
    public=True,
    permission_classes=[AllowAny],
)

urlpatterns = [
    path("", warga.index, name="index"),
    path("warga/form-warga/<int:idwarga>", warga.formWarga, name="formWarga"),
    path(
        "warga/set-kk/<int:idwarga>",
        warga.set_kepala_keluarga,
        name="set_kepala_keluarga",
    ),
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
    path("warga/statistic", utility.statistic_warga, name="statisticWarga"),
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
    path(
        "public/dashboard/<str:page>", utility.dashboard_public, name="publicDasboard"
    ),
    path("public/iuran", iuran_public.form_iuran_bulanan_display, name="publicIuran"),
    path(
        "warga/summary-iuranbulanan-form",
        iuran.pdfReportIuranBulananForm,
        name="pdfReportIuranBulananForm",
    ),
    path(
        "warga/summary-iuranbulanan-pdf/<int:year>",
        iuran.pdf_report_iuranbulanan,
        name="pdfReportIuranBulanan",
    ),
    path(
        "warga/iuran-income-statement",
        iuran.iuranIncomeStatementReportForm,
        name="iuranIncomeStatementReportForm",
    ),
    path(
        "warga/iuran-income-statement-pdf",
        iuran.iuranIncomeStatementReportFormExec,
        name="iuranIncomeStatementReportFormExec",
    ),
    path("warga/iuran-yearly", iuran.iuranYearly, name="iuranYearly"),
    path("api/", include(router.urls)),
    path("api/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path(
        "swagger/",
        schema_view.with_ui("swagger", cache_timeout=0),
        name="schema-swagger-ui",
    ),
    path("redoc/", schema_view.with_ui("redoc", cache_timeout=0), name="schema-redoc"),
]

if settings.WG_ENV == "dev":
    urlpatterns.append(path("generate/<int:count>", utility.generate_data_warga))
