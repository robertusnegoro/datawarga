from .models import Warga, Kompleks, TransaksiIuranBulanan
from .serializers import wargaSerializer, kompleksSerializer, iuranSerializer
from django.db.models import Q
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
import logging
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser

logger = logging.getLogger(__name__)


class wargaViewSet(viewsets.ModelViewSet):
    queryset = Warga.objects.order_by("id")
    serializer_class = wargaSerializer
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=["post"], url_path="search")
    def search(self, request, *args, **kwargs):
        if request.method == "POST":
            search_term = request.data.get("search", "")
            
            # Check if search term contains blok/nomor format
            if "/" in search_term:
                split_keyword = search_term.split("/")
                queryset = self.queryset.filter(
                    kompleks__blok__icontains=split_keyword[0].strip(),
                    kompleks__nomor=split_keyword[1].strip(),
                )
            else:
                # Original search plus kompleks search
                queryset = self.queryset.filter(
                    Q(nama_lengkap__icontains=search_term) | 
                    Q(nik__icontains=search_term) |
                    Q(kompleks__blok__icontains=search_term) |
                    Q(kompleks__nomor__icontains=search_term)
                )
            logger.info(f"search to warga models with keyword {search_term}")
        else:
            queryset = self.queryset
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class iuranViewSet(viewsets.ModelViewSet):
    queryset = TransaksiIuranBulanan.objects.order_by("id")
    serializer_class = iuranSerializer
    permission_classes = [IsAuthenticated]


class kompleksViewSet(viewsets.ModelViewSet):
    queryset = Kompleks.objects.order_by("id")
    serializer_class = kompleksSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = (MultiPartParser, FormParser, JSONParser)

    @action(detail=False, methods=["post"], url_path="search")
    def search(self, request, *args, **kwargs):
        if request.method == "POST":
            search_term = request.data.get("search", "")

            if "/" in search_term:
                split_keyword = search_term.split("/")
                queryset = self.queryset.filter(
                    blok__icontains=split_keyword[0].strip(),
                    nomor=split_keyword[1].strip(),
                )
            else:
                queryset = self.queryset.filter(
                    Q(cluster__icontains=search_term) | Q(blok__icontains=search_term)
                )
                logger.info(f"search to kompleks models with keyword {search_term}")
        else:
            queryset = self.queryset
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["post"], url_path="warga")
    def warga(self, request, *args, **kwargs):
        queryset = Warga.objects.none()  # Initialize with empty queryset
        
        if request.method == "POST":
            search_term = request.data.get("blok_no", "")

            if "/" in search_term:
                split_keyword = search_term.split("/")
                data_kompleks = self.queryset.filter(
                    blok__icontains=split_keyword[0].strip(),
                    nomor=split_keyword[1].strip(),
                )
                total_kompleks = len(data_kompleks)
                if total_kompleks > 0:
                    idkompleks = data_kompleks[0].pk
                    queryset = Warga.objects.filter(kompleks=idkompleks).filter(
                        ~Q(status_tinggal="PINDAH")
                    )
                else:
                    return Response({}, status=status.HTTP_204_NO_CONTENT)
            else:
                return Response({}, status=status.HTTP_204_NO_CONTENT)

        serializer = wargaSerializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["post"], url_path="iuran")
    def iuran(self, request, *args, **kwargs):
        queryset = TransaksiIuranBulanan.objects.none()
        
        if request.method == "POST":
            if request.content_type == 'application/json':
                data = request.data
            else:
                data = request.POST
                
            search_term = data.get("blok_no", "")
            try:
                tahun = int(data.get("tahun", 0))
            except (TypeError, ValueError):
                return Response({"error": "Invalid year"}, status=status.HTTP_400_BAD_REQUEST)

            if "/" in search_term:
                split_keyword = search_term.split("/")
                data_kompleks = self.queryset.filter(
                    blok__icontains=split_keyword[0].strip(),
                    nomor=split_keyword[1].strip(),
                )
                total_kompleks = len(data_kompleks)
                if total_kompleks > 0:
                    idkompleks = data_kompleks[0].pk
                    queryset = TransaksiIuranBulanan.objects.filter(
                        kompleks=idkompleks
                    ).filter(periode_tahun=tahun)
                else:
                    return Response({}, status=status.HTTP_204_NO_CONTENT)
            else:
                return Response({}, status=status.HTTP_204_NO_CONTENT)

        serializer = iuranSerializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["post"], url_path="bayar")
    def bayar(self, request, *args, **kwargs):
        search_term = request.data.get("blok_no", "")
        periode_bulan = request.data.get("periode_bulan")
        periode_tahun = request.data.get("periode_tahun")
        total_bayar = request.data.get("total_bayar")
        bukti_bayar = request.FILES.get("bukti_bayar")

        if "/" not in search_term:
            return Response({"error": "Format alamat tidak valid"}, status=status.HTTP_400_BAD_REQUEST)

        split_keyword = search_term.split("/")
        data_kompleks = self.queryset.filter(
            blok__icontains=split_keyword[0].strip(),
            nomor=split_keyword[1].strip(),
        )

        if not data_kompleks.exists():
            return Response({"error": "Alamat tidak ditemukan"}, status=status.HTTP_404_NOT_FOUND)

        # Check if payment already exists
        existing_payment = TransaksiIuranBulanan.objects.filter(
            kompleks=data_kompleks[0],
            periode_bulan=periode_bulan,
            periode_tahun=periode_tahun
        ).exists()

        if existing_payment:
            return Response(
                {"error": f"Pembayaran untuk periode {periode_bulan}/{periode_tahun} sudah ada"}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        # Record payment
        try:
            payment = TransaksiIuranBulanan.objects.create(
                kompleks=data_kompleks[0],
                periode_bulan=periode_bulan,
                periode_tahun=periode_tahun,
                total_bayar=total_bayar,
                bukti_bayar=bukti_bayar
            )
            serializer = iuranSerializer(payment)
            return Response(serializer.data)
        except Exception as e:
            logger.error(f"Failed to record payment: {str(e)}")
            return Response(
                {"error": "Gagal mencatat pembayaran"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
