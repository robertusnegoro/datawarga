from django.urls import path, re_path
from . import views
from django.conf import settings

app_name = "kependudukan"


urlpatterns = [
    path("", views.index, name="index"),
    path("form-warga/<int:idwarga>", views.formWarga, name="formWarga"),
    path(
        "delete-form-warga/<int:idwarga>", views.deleteFormWarga, name="deleteformWarga"
    ),
    path("form-warga-simpan", views.formWargaSimpan, name="formWargaSimpan"),
    path("list-warga-view", views.WargaListView.as_view(), name="listWargaView"),
    path("test-view", views.testView, name="testView"),
    path("data-warga-pdf", views.listWargaReport, name="dataWargaPDF"),
    path("dashboard-report", views.dashboard_warga, name="dashboardWarga"),
    path("form-kompleks", views.kompleks_form, name="kompleksForm"),
    path("generate-kompleks-exec", views.generate_kompleks, name="generateKompleks"),
    re_path(
        r"^%s(?P<path>.*)$" % settings.MEDIA_URL[1:],
        views.protected_serve,
        {"document_root": settings.MEDIA_ROOT},
    ),
]

if settings.WG_ENV == "dev":
    urlpatterns.append(path("generate/<int:count>", views.generate_data_warga))
