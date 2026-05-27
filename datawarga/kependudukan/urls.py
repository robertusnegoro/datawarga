from django.urls import path, re_path, include
from .views import (
    utility,
    kompleks,
    warga,
    iuran,
    iuran_public,
    api as api_view,
    surat as views_surat,
    kendaraan as views_kendaraan,
    kas as views_kas,
    profile as views_profile,
    admin as views_admin,
)
from django.conf import settings
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
router.register(r"kompleks", api_view.kompleksViewSet)
router.register(r"iuran", api_view.iuranViewSet)

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
    path("warga/detail/<int:idwarga>", warga.detailWarga, name="detailWarga"),
    path(
        "warga/detail/<int:idwarga>/kendaraan/tambah",
        views_kendaraan.form_kendaraan,
        name="formKendaraan",
    ),
    path(
        "warga/detail/<int:idwarga>/kendaraan/<int:idkendaraan>",
        views_kendaraan.form_kendaraan,
        name="formKendaraanEdit",
    ),
    path(
        "warga/kendaraan/simpan",
        views_kendaraan.form_kendaraan_save,
        name="formKendaraanSave",
    ),
    path(
        "warga/kendaraan/<int:idkendaraan>/hapus",
        views_kendaraan.delete_kendaraan,
        name="deleteKendaraan",
    ),
    path("warga/detail/<int:idwarga>/pdf", warga.pdfDetailWarga, name="pdfDetailWarga"),
    path("warga/list-warga-view", warga.WargaListView.as_view(), name="listWargaView"),
    path(
        "warga/arsip-warga-view",
        warga.ArsipWargaListView.as_view(),
        name="arsipWargaView",
    ),
    path(
        "warga/daftar-kepala-keluarga",
        warga.KepalaKeluargaListView.as_view(),
        name="daftarKepalaKeluarga",
    ),
    path(
        "warga/detail-anggota-keluarga/<int:idkompleks>",
        warga.detail_anggota_keluarga_snippet,
        name="detailAnggotaKeluarga",
    ),
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
        "warga/kompleks/<int:idkompleks>/iuran/batch/<str:year>",
        iuran.form_batch_iuran_bulanan,
        name="batchIuranBulanan",
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
    path("warga/scan-ktp", warga.scan_ktp_ajax, name="scan_ktp_ajax"),
    # Citizen (Warga) Portal URL Patterns
    path("warga/dashboard/", warga.warga_dashboard, name="warga_dashboard"),
    path("warga/request-surat/", warga.warga_request_surat, name="warga_request_surat"),
    path(
        "warga/register-kendaraan/",
        warga.warga_register_kendaraan,
        name="warga_register_kendaraan",
    ),
    path("warga/upload-iuran/", warga.warga_upload_iuran, name="warga_upload_iuran"),
    path("warga/submit-update/", warga.warga_submit_update, name="warga_submit_update"),
    path("warga/admin/approvals/", views_admin.admin_approvals, name="admin_approvals"),
    path(
        "warga/invite-login/<int:idwarga>/",
        views_admin.warga_invite_login,
        name="warga_invite_login",
    ),
    path(
        "warga/detail/<int:idwarga>/buat-surat",
        views_surat.form_surat,
        name="form_surat",
    ),
    path("surat/cetak/<int:idsurat>", views_surat.cetak_surat, name="cetak_surat"),
    path(
        "surat/cetak/<int:idsurat>/pdf",
        views_surat.cetak_surat_pdf,
        name="cetak_surat_pdf",
    ),
    path("surat/list", views_surat.list_surat, name="list_surat"),
    path(
        "surat/delete/<int:idsurat>",
        views_surat.delete_surat,
        name="delete_surat",
    ),
    # Kas & Keuangan RT/RW
    path("warga/kas/", views_kas.dashboard_kas, name="dashboard_kas"),
    path(
        "warga/kas/transaksi/", views_kas.list_kas_transaksi, name="list_kas_transaksi"
    ),
    path(
        "warga/kas/transaksi/tambah/",
        views_kas.form_kas_transaksi,
        name="form_kas_transaksi",
    ),
    path(
        "warga/kas/transaksi/edit/<int:idtransaksi>",
        views_kas.form_kas_transaksi,
        name="edit_kas_transaksi",
    ),
    path(
        "warga/kas/transaksi/hapus/<int:idtransaksi>",
        views_kas.delete_kas_transaksi,
        name="delete_kas_transaksi",
    ),
    path("warga/kas/tagihan/", views_kas.list_kas_tagihan, name="list_kas_tagihan"),
    path(
        "warga/kas/tagihan/tambah/", views_kas.form_kas_tagihan, name="form_kas_tagihan"
    ),
    path(
        "warga/kas/tagihan/edit/<int:idtagihan>",
        views_kas.form_kas_tagihan,
        name="edit_kas_tagihan",
    ),
    path(
        "warga/kas/tagihan/hapus/<int:idtagihan>",
        views_kas.delete_kas_tagihan,
        name="delete_kas_tagihan",
    ),
    path(
        "warga/kas/tagihan/bayar/<int:idtagihan>",
        views_kas.bayar_tagihan,
        name="bayar_tagihan",
    ),
    path(
        "warga/kas/sync-iuran/", views_kas.sync_iuran_to_kas, name="sync_iuran_to_kas"
    ),
    path("warga/kas/laporan/", views_kas.laporan_kas, name="laporan_kas"),
    path("warga/kas/laporan/pdf/", views_kas.pdf_report_kas, name="pdf_report_kas"),
    path("profile/", views_profile.profile_edit, name="profile_edit"),
    path("accounts/login/mfa/", views_profile.mfa_verify, name="mfa_verify"),
    path("profile/mfa/setup/", views_profile.mfa_setup, name="mfa_setup"),
    path("profile/mfa/disable/", views_profile.mfa_disable, name="mfa_disable"),
    # Admin Panel User Management
    path("warga/admin/users/", views_admin.user_management, name="user_management"),
    path("warga/admin/users/add/", views_admin.user_add, name="user_add"),
    path(
        "warga/admin/users/edit/<int:user_id>/", views_admin.user_edit, name="user_edit"
    ),
    path(
        "warga/admin/users/block/<int:user_id>/",
        views_admin.user_block,
        name="user_block",
    ),
    path(
        "warga/admin/users/unblock/<int:user_id>/",
        views_admin.user_unblock,
        name="user_unblock",
    ),
    path(
        "warga/admin/users/reset-mfa/<int:user_id>/",
        views_admin.user_reset_mfa,
        name="user_reset_mfa",
    ),
    path(
        "warga/admin/users/reset-password/<int:user_id>/",
        views_admin.user_reset_password,
        name="user_reset_password",
    ),
    path(
        "warga/admin/users/expire-invitation/<int:user_id>/",
        views_admin.invitation_expire,
        name="invitation_expire",
    ),
    path(
        "warga/admin/users/recreate-invitation/<int:user_id>/",
        views_admin.invitation_recreate,
        name="invitation_recreate",
    ),
    # Public invitation activation route
    path(
        "accounts/invite/<str:token>/", views_admin.user_activate, name="user_activate"
    ),
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
