from .models import Warga, Kompleks
from django import forms


class WargaForm(forms.ModelForm):
    class Meta:
        model = Warga
        fields = "__all__"


class KompleksForm(forms.ModelForm):
    class Meta:
        model = Kompleks
        fields = "__all__"


class GenerateKompleksForm(forms.Form):
    cluster = forms.CharField(label="Cluster", max_length=150, required=False)
    blok = forms.CharField(label="Blok", max_length=10)
    rt = forms.CharField(label="rt", max_length=4)
    rw = forms.CharField(label="rw", max_length=4)
    total_num = forms.IntegerField(label="Jumlah Nomor")
