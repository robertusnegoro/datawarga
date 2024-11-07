from rest_framework import serializers
from .models import Warga, Kompleks


class kompleksSerializer(serializers.ModelSerializer):
    class Meta:
        model = Kompleks
        fields = "__all__"


class wargaSerializer(serializers.ModelSerializer):
    kompleks = kompleksSerializer()

    class Meta:
        model = Warga
        fields = "__all__"
