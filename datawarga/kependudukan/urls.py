from django.urls import path
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
]
