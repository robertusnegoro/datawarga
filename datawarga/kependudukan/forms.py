from django.contrib.auth.models import User
from .models import (
    Warga,
    Kompleks,
    TransaksiIuranBulanan,
    Kendaraan,
    KasTransaksi,
    KasTagihan,
    UserProfile,
)
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


class IuranBulananForm(forms.ModelForm):
    class Meta:
        model = TransaksiIuranBulanan
        fields = [
            "keterangan",
            "bukti_bayar",
            "periode_bulan",
            "periode_tahun",
            "total_bayar",
            "kompleks",
        ]


class BatchIuranBulananForm(forms.Form):
    BULAN_CHOICES = [
        ("1", "Januari"),
        ("2", "Februari"),
        ("3", "Maret"),
        ("4", "April"),
        ("5", "Mei"),
        ("6", "Juni"),
        ("7", "Juli"),
        ("8", "Agustus"),
        ("9", "September"),
        ("10", "Oktober"),
        ("11", "November"),
        ("12", "Desember"),
    ]

    periode_tahun = forms.CharField(max_length=4)
    bulan = forms.MultipleChoiceField(
        choices=BULAN_CHOICES, widget=forms.CheckboxSelectMultiple, required=True
    )
    total_bayar = forms.IntegerField(initial=settings.IURAN_BULANAN)
    keterangan = forms.CharField(max_length=255, required=False)
    bukti_bayar = forms.FileField(required=False)


class KendaraanForm(forms.ModelForm):
    class Meta:
        model = Kendaraan
        fields = "__all__"


class KasTransaksiForm(forms.ModelForm):
    class Meta:
        model = KasTransaksi
        fields = [
            "tanggal",
            "jenis",
            "kategori",
            "jumlah",
            "keterangan",
            "bukti_transaksi",
        ]
        widgets = {
            "tanggal": forms.DateInput(attrs={"type": "date"}),
            "keterangan": forms.Textarea(attrs={"rows": 3}),
        }


class KasTagihanForm(forms.ModelForm):
    class Meta:
        model = KasTagihan
        fields = [
            "judul",
            "jenis",
            "kategori",
            "jumlah",
            "tanggal_jatuh_tempo",
            "status",
            "keterangan",
        ]
        widgets = {
            "tanggal_jatuh_tempo": forms.DateInput(attrs={"type": "date"}),
            "keterangan": forms.Textarea(attrs={"rows": 3}),
        }


class UserUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["first_name", "last_name", "email"]
        widgets = {
            "first_name": forms.TextInput(attrs={"class": "form-control"}),
            "last_name": forms.TextInput(attrs={"class": "form-control"}),
            "email": forms.EmailInput(attrs={"class": "form-control"}),
        }


class UserProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ["foto"]
        widgets = {
            "foto": forms.FileInput(attrs={"class": "form-control-file"}),
        }


class UserAddForm(forms.ModelForm):
    email = forms.EmailField(
        required=True, widget=forms.EmailInput(attrs={"class": "form-control"})
    )

    class Meta:
        model = User
        fields = ["username", "email", "first_name", "last_name"]
        widgets = {
            "username": forms.TextInput(attrs={"class": "form-control"}),
            "first_name": forms.TextInput(attrs={"class": "form-control"}),
            "last_name": forms.TextInput(attrs={"class": "form-control"}),
        }

    def clean_email(self):
        email = self.cleaned_data.get("email")
        if email and User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("Email ini sudah terdaftar.")
        return email


class UserEditForm(forms.ModelForm):
    email = forms.EmailField(
        required=True, widget=forms.EmailInput(attrs={"class": "form-control"})
    )

    class Meta:
        model = User
        fields = ["email", "first_name", "last_name"]
        widgets = {
            "first_name": forms.TextInput(attrs={"class": "form-control"}),
            "last_name": forms.TextInput(attrs={"class": "form-control"}),
        }

    def clean_email(self):
        email = self.cleaned_data.get("email")
        if email:
            qs = User.objects.filter(email__iexact=email)
            if self.instance and self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError("Email ini sudah terdaftar.")
        return email


class MfaVerifyForm(forms.Form):
    token = forms.CharField(
        max_length=6,
        min_length=6,
        required=True,
        widget=forms.TextInput(
            attrs={
                "class": "form-control text-center font-weight-bold",
                "placeholder": "123456",
                "pattern": "[0-9]{6}",
                "inputmode": "numeric",
                "autocomplete": "one-time-code",
                "style": "font-size: 1.5rem; letter-spacing: 0.5rem;",
            }
        ),
        label="Kode Verification (6 Digit)",
    )
