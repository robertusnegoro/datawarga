from .models import Warga, Kompleks
from django import forms
from django.conf import settings
from django.core.validators import FileExtensionValidator


class WargaForm(forms.ModelForm):
    class Meta:
        model = Warga
        fields = "__all__"


class KompleksForm(forms.ModelForm):
    class Meta:
        model = Kompleks
        fields = "__all__"


class GenerateKompleksForm(forms.Form):
    alamat = forms.CharField(
        label="Alamat", max_length=255, required=False, initial=settings.ALAMAT
    )
    kecamatan = forms.CharField(
        label="Kecamatan", max_length=150, initial=settings.KECAMATAN
    )
    kelurahan = forms.CharField(
        label="Kelurahan", max_length=150, initial=settings.KECAMATAN
    )
    kota = forms.CharField(label="Kota", max_length=150, initial=settings.KECAMATAN)
    provinsi = forms.CharField(
        label="Provinsi", max_length=150, initial=settings.KECAMATAN
    )
    kode_pos = forms.CharField(label="Kode Pos", max_length=8, required=False)
    cluster = forms.CharField(label="Cluster", max_length=150, required=False)
    blok = forms.CharField(label="Blok", max_length=10)
    rt = forms.CharField(label="rt", max_length=4)
    rw = forms.CharField(label="rw", max_length=4)
    start_num = forms.IntegerField(label="Nomor Awal")
    finish_num = forms.IntegerField(label="Nomor Akhir")


class WargaCSVForm(forms.Form):
    csv_file = forms.FileField(
        label="CSV File",
        validators=[FileExtensionValidator(allowed_extensions=["csv"])],
    )
