from .models import Warga
from django import forms


class WargaForm(forms.ModelForm):
    class Meta:
        model = Warga
        fields = "__all__"
