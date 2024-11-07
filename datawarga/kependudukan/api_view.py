from .models import Warga
from .serializers import wargaSerializer
from django.db.models import Q
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
import logging

logger = logging.getLogger(__name__)


class wargaViewSet(viewsets.ModelViewSet):
    queryset = Warga.objects.order_by("id")
    serializer_class = wargaSerializer
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=["post"], url_path="search")
    def search(self, request, *args, **kwargs):
        if request.method == "POST":
            search_term = request.data.get("search", "")
            queryset = self.queryset.filter(
                Q(nama_lengkap__icontains=search_term) | Q(nik__icontains=search_term)
            )
            logger.info(f"search to warga models with keyword {search_term}")
        else:
            queryset = self.queryset
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
