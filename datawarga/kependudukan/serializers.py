from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
import pyotp

from .models import (
    Warga,
    Kompleks,
    TransaksiIuranBulanan,
    WargaUpdateRequest,
    Surat,
    Kendaraan,
)


class kompleksSerializer(serializers.ModelSerializer):
    class Meta:
        model = Kompleks
        fields = [
            "id",
            "alamat",
            "kecamatan",
            "kelurahan",
            "kode_pos",
            "kota",
            "provinsi",
            "cluster",
            "blok",
            "nomor",
            "description",
            "rt",
            "rw",
        ]


class wargaSerializer(serializers.ModelSerializer):
    kompleks = kompleksSerializer()

    class Meta:
        model = Warga
        fields = "__all__"


class iuranSerializer(serializers.ModelSerializer):
    kompleks = kompleksSerializer()

    class Meta:
        model = TransaksiIuranBulanan
        fields = "__all__"


class WargaMeUpdateRequestSerializer(serializers.Serializer):
    target_warga_id = serializers.CharField(
        required=False, help_text="ID of target warga or 'NEW'"
    )
    nama_lengkap = serializers.CharField(required=False)
    nik = serializers.CharField(required=False)
    no_hp = serializers.CharField(required=False)
    no_kk = serializers.CharField(required=False)
    pekerjaan = serializers.CharField(required=False)
    agama = serializers.CharField(required=False)
    status = serializers.CharField(required=False)
    tanggal_lahir = serializers.DateField(required=False)
    tempat_lahir = serializers.CharField(required=False)
    jenis_kelamin = serializers.CharField(required=False)
    kewarganegaraan = serializers.CharField(required=False)
    status_tinggal = serializers.CharField(required=False)
    status_keluarga = serializers.CharField(required=False)
    alamat_ktp = serializers.CharField(required=False)
    foto_path = serializers.FileField(required=False)
    ktp_image_path = serializers.FileField(required=False)


class WargaUpdateRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = WargaUpdateRequest
        fields = [
            "id",
            "warga",
            "requested_by",
            "kompleks",
            "is_new_warga",
            "data_changes",
            "foto_path",
            "ktp_image_path",
            "status",
            "notes",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "warga",
            "requested_by",
            "kompleks",
            "is_new_warga",
            "status",
            "notes",
            "created_at",
            "updated_at",
        ]


class SuratRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = Surat
        fields = [
            "id",
            "warga",
            "jenis_surat",
            "keperluan",
            "tanggal_surat",
            "status",
            "keterangan_status",
        ]
        read_only_fields = [
            "id",
            "warga",
            "tanggal_surat",
            "status",
            "keterangan_status",
        ]


class KendaraanRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = Kendaraan
        fields = [
            "id",
            "pemilik",
            "jenis_kendaraan",
            "merk",
            "tipe",
            "plat_nomor",
            "keterangan",
            "status",
            "keterangan_status",
        ]
        read_only_fields = ["id", "pemilik", "status", "keterangan_status"]


class IuranRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = TransaksiIuranBulanan
        fields = [
            "id",
            "kompleks",
            "periode_bulan",
            "periode_tahun",
            "total_bayar",
            "bukti_bayar",
            "keterangan",
            "status",
            "keterangan_status",
        ]
        read_only_fields = ["id", "kompleks", "status", "keterangan_status"]


class KtpScanRequestSerializer(serializers.Serializer):
    ktp_image = serializers.FileField(
        help_text="File foto KTP (ktp_image) harus dilampirkan."
    )


class UserProfileDetailSerializer(serializers.ModelSerializer):
    username = serializers.CharField(read_only=True)
    email = serializers.EmailField(required=True)
    first_name = serializers.CharField(required=False, allow_blank=True)
    last_name = serializers.CharField(required=False, allow_blank=True)
    foto = serializers.ImageField(
        source="profile.foto", required=False, allow_null=True
    )
    mfa_enabled = serializers.BooleanField(source="profile.mfa_enabled", read_only=True)
    role = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "foto",
            "mfa_enabled",
            "role",
        ]

    def get_role(self, obj):
        from .utils.auth_guards import is_admin_or_petugas
        return "admin" if is_admin_or_petugas(obj) else "warga"

    def validate_email(self, value):
        user = self.context["request"].user
        if User.objects.filter(email__iexact=value).exclude(pk=user.pk).exists():
            raise serializers.ValidationError("Email ini sudah terdaftar.")
        return value

    def update(self, instance, validated_data):
        # Update User fields
        instance.email = validated_data.get("email", instance.email)
        instance.first_name = validated_data.get("first_name", instance.first_name)
        instance.last_name = validated_data.get("last_name", instance.last_name)
        instance.save()

        # Update UserProfile fields (e.g. foto)
        profile_data = validated_data.get("profile", {})
        if "foto" in profile_data:
            profile = instance.profile
            profile.foto = profile_data["foto"]
            profile.save()

        return instance


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True, write_only=True)
    new_password = serializers.CharField(required=True, write_only=True)
    confirm_password = serializers.CharField(required=True, write_only=True)

    def validate_old_password(self, value):
        user = self.context["request"].user
        if not user.check_password(value):
            raise serializers.ValidationError("Kata sandi lama salah.")
        return value

    def validate(self, data):
        if data["new_password"] != data["confirm_password"]:
            raise serializers.ValidationError(
                {"confirm_password": "Konfirmasi kata sandi tidak cocok."}
            )
        try:
            validate_password(data["new_password"], self.context["request"].user)
        except Exception as e:
            from django.core.exceptions import ValidationError as DjangoValidationError

            if isinstance(e, DjangoValidationError):
                raise serializers.ValidationError({"new_password": list(e.messages)})
            raise e
        return data


class MfaEnableSerializer(serializers.Serializer):
    secret_key = serializers.CharField(required=True)
    token = serializers.CharField(required=True, min_length=6, max_length=6)


class MfaDisableSerializer(serializers.Serializer):
    token = serializers.CharField(required=True, min_length=6, max_length=6)


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    mfa_token = serializers.CharField(
        required=False, min_length=6, max_length=6, allow_blank=True
    )

    def validate(self, attrs):
        # The default validate method validates the user credentials and sets self.user
        data = super().validate(attrs)

        if hasattr(self.user, "profile") and self.user.profile.mfa_enabled:
            mfa_token = attrs.get("mfa_token", "").strip()
            if not mfa_token:
                raise serializers.ValidationError(
                    {"mfa_token": "MFA token is required for this account."}
                )

            totp = pyotp.TOTP(self.user.profile.totp_secret)
            if not totp.verify(mfa_token):
                raise serializers.ValidationError({"mfa_token": "Invalid MFA token."})

        return data
