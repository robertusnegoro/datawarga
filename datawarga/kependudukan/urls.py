from django.urls import path
from . import views
from django.conf import settings

app_name = "kependudukan"


urlpatterns = [
    path("", views.index, name="index"),
    path("form-warga", views.formWarga, name="form"),
]
