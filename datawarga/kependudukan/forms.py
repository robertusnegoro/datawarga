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
