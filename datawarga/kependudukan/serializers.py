from rest_framework import serializers
from .models import Warga, Kompleks, TransaksiIuranBulanan


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
