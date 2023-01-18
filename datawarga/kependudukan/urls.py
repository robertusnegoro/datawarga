from django.urls import path, re_path
from . import views
from django.conf import settings

app_name = "kependudukan"


urlpatterns = [
    path("", views.index, name="index"),
    path("warga/form-warga/<int:idwarga>", views.formWarga, name="formWarga"),
    path(
        "warga/delete-form-warga/<int:idwarga>", views.deleteFormWarga, name="deleteformWarga"
    ),
    path("warga/form-warga-simpan", views.formWargaSimpan, name="formWargaSimpan"),
    path("warga/list-warga-view", views.WargaListView.as_view(), name="listWargaView"),
    path("warga/test-view", views.testView, name="testView"),
    path("warga/data-warga-pdf", views.listWargaReport, name="dataWargaPDF"),
    path("warga/dashboard-report", views.dashboard_warga, name="dashboardWarga"),
    path("warga/form-kompleks", views.kompleks_form, name="kompleksForm"),
    path("warga/generate-kompleks-exec", views.generate_kompleks, name="generateKompleks"),
    path(
        "warga/list-kompleks-view", views.KompleksListView.as_view(), name="listKompleksView"
    ),
    path("warga/delete-blok-form", views.delete_blok_form, name="deleteBlokForm"),
    path(
        "warga/detail-kompleks/<int:idkompleks>", views.detail_kompleks, name="detailKompleks"
    ),
    path("warga/warga-rumah/<int:idkompleks>", views.warga_rumah, name="wargaRumah"),
    path("warga/form-warga-rumah/<int:idkompleks>", views.form_warga_rumah, name="formWargaRumah"),
    re_path(
        r"^%s(?P<path>.*)$" % settings.MEDIA_URL[1:],
        views.protected_serve,
        {"document_root": settings.MEDIA_ROOT},
    ),
]

if settings.WG_ENV == "dev":
    urlpatterns.append(path("generate/<int:count>", views.generate_data_warga))
