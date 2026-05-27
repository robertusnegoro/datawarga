from rest_framework import serializers
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
