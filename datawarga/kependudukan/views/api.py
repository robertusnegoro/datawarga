from kependudukan.models import Warga, Kompleks, TransaksiIuranBulanan
from kependudukan.serializers import (
    wargaSerializer,
    kompleksSerializer,
    iuranSerializer,
)
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
import logging
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from kependudukan.selectors.warga_selector import search_warga_queryset
from kependudukan.selectors.kompleks_selector import search_kompleks_queryset
from kependudukan.services.iuran_service import record_iuran_payment
from kependudukan.errors import DatawargaError
from kependudukan.utils.auth_guards import IsAdminOrPetugas

logger = logging.getLogger(__name__)


class wargaViewSet(viewsets.ModelViewSet):
    queryset = Warga.objects.order_by("id")
    serializer_class = wargaSerializer
    permission_classes = [IsAuthenticated, IsAdminOrPetugas]

    def get_permissions(self):
        if self.action in [
            "me",
            "me_update",
            "me_requests",
            "me_surat",
            "me_kendaraan",
            "me_iuran",
        ]:
            return [IsAuthenticated()]
        return [IsAuthenticated(), IsAdminOrPetugas()]

    def _get_warga(self, request):
        if not hasattr(request.user, "warga") or request.user.warga is None:
            from rest_framework.exceptions import PermissionDenied

            raise PermissionDenied(
                "Hanya warga terdaftar yang dapat mengakses portal ini."
            )
        return request.user.warga

    @action(detail=False, methods=["get"], url_path="me")
    def me(self, request):
        warga = self._get_warga(request)
        serializer = self.get_serializer(warga)
        return Response(serializer.data)

    @action(
        detail=False,
        methods=["post"],
        url_path="me/update",
        parser_classes=(MultiPartParser, FormParser, JSONParser),
    )
    def me_update(self, request):
        warga = self._get_warga(request)
        
        target_warga_id = request.data.get("target_warga_id")
        target_warga = None
        is_new_warga = False
        
        if target_warga_id == "NEW":
            is_new_warga = True
        elif target_warga_id:
            try:
                from kependudukan.models import Warga
                target_warga = Warga.objects.get(pk=target_warga_id)
                if not (target_warga == warga or (warga.kompleks and target_warga.kompleks == warga.kompleks)):
                    return Response(
                        {"error": "Target warga tidak valid atau tidak berada dalam satu rumah."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
            except Warga.DoesNotExist:
                return Response(
                    {"error": "Target warga tidak ditemukan."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        else:
            target_warga = warga

        updatable_fields = [
            "nama_lengkap",
            "nik",
            "no_hp",
            "no_kk",
            "pekerjaan",
            "agama",
            "status",
            "tanggal_lahir",
            "tempat_lahir",
            "jenis_kelamin",
            "kewarganegaraan",
            "status_tinggal",
            "status_keluarga",
            "alamat_ktp",
        ]
        changes = {}
        for field in updatable_fields:
            val = request.data.get(field)
            if val is not None:
                changes[field] = str(val).strip()

        files = {}
        if "foto_path" in request.FILES:
            files["foto_path"] = request.FILES["foto_path"]
        if "ktp_image_path" in request.FILES:
            files["ktp_image_path"] = request.FILES["ktp_image_path"]

        from kependudukan.services.warga_service import submit_warga_update_request
        from kependudukan.serializers import WargaUpdateRequestSerializer

        update_request = submit_warga_update_request(
            warga=target_warga,
            fields_data=changes,
            files=files,
            requested_by=warga,
            is_new_warga=is_new_warga,
            kompleks=warga.kompleks
        )
        serializer = WargaUpdateRequestSerializer(update_request)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["get"], url_path="me/requests")
    def me_requests(self, request):
        warga = self._get_warga(request)
        from kependudukan.models import WargaUpdateRequest
        from kependudukan.serializers import WargaUpdateRequestSerializer
        from django.db.models import Q

        queryset = WargaUpdateRequest.objects.filter(
            Q(warga=warga) | Q(requested_by=warga)
        ).distinct().order_by("-created_at")
        serializer = WargaUpdateRequestSerializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get", "post"], url_path="me/surat")
    def me_surat(self, request):
        warga = self._get_warga(request)
        from kependudukan.models import Surat
        from kependudukan.serializers import SuratRequestSerializer

        if request.method == "POST":
            jenis_surat = request.data.get("jenis_surat")
            keperluan = request.data.get("keperluan", "").strip()

            if not jenis_surat or not keperluan:
                return Response(
                    {"error": "Jenis surat dan keperluan harus diisi."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            surat = Surat.objects.create(
                warga=warga,
                jenis_surat=jenis_surat,
                keperluan=keperluan,
                status="PENDING",
            )
            serializer = SuratRequestSerializer(surat)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        queryset = Surat.objects.filter(warga=warga).order_by("-tanggal_surat")
        serializer = SuratRequestSerializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get", "post"], url_path="me/kendaraan")
    def me_kendaraan(self, request):
        warga = self._get_warga(request)
        from kependudukan.models import Kendaraan
        from kependudukan.serializers import KendaraanRequestSerializer

        if request.method == "POST":
            jenis_kendaraan = request.data.get("jenis_kendaraan", "MOBIL")
            merk = request.data.get("merk", "").strip()
            tipe = request.data.get("tipe", "").strip()
            plat_nomor = request.data.get("plat_nomor", "").strip().upper()
            keterangan = request.data.get("keterangan", "").strip()

            if not plat_nomor:
                return Response(
                    {"error": "Plat nomor kendaraan harus diisi."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if Kendaraan.objects.filter(plat_nomor=plat_nomor).exists():
                return Response(
                    {"error": f"Plat nomor {plat_nomor} sudah terdaftar."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            kendaraan = Kendaraan.objects.create(
                pemilik=warga,
                jenis_kendaraan=jenis_kendaraan,
                merk=merk,
                tipe=tipe,
                plat_nomor=plat_nomor,
                keterangan=keterangan,
                status="PENDING",
            )
            serializer = KendaraanRequestSerializer(kendaraan)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        queryset = Kendaraan.objects.filter(pemilik=warga).order_by("-id")
        serializer = KendaraanRequestSerializer(queryset, many=True)
        return Response(serializer.data)

    @action(
        detail=False,
        methods=["get", "post"],
        url_path="me/iuran",
        parser_classes=(MultiPartParser, FormParser, JSONParser),
    )
    def me_iuran(self, request):
        warga = self._get_warga(request)
        from kependudukan.models import TransaksiIuranBulanan
        from kependudukan.serializers import IuranRequestSerializer

        if request.method == "POST":
            if not warga.kompleks:
                return Response(
                    {
                        "error": "Akun Anda belum terasosiasi dengan nomor rumah/kompleks. Hubungi admin."
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            try:
                periode_bulan = int(request.data.get("periode_bulan", 0))
                periode_tahun = int(request.data.get("periode_tahun", 0))
                from django.conf import settings

                total_bayar_val = request.data.get("total_bayar")
                if total_bayar_val is not None and str(total_bayar_val).strip() != "":
                    total_bayar = int(total_bayar_val)
                else:
                    total_bayar = settings.IURAN_BULANAN
            except (TypeError, ValueError):
                return Response(
                    {
                        "error": "Input periode bulan, tahun, atau total iuran tidak valid."
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            bukti_bayar = request.FILES.get("bukti_bayar")
            keterangan = request.data.get("keterangan", "").strip()

            if not periode_bulan or not periode_tahun or not bukti_bayar:
                return Response(
                    {
                        "error": "Bulan, tahun, and file bukti pembayaran harus dilampirkan."
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            existing = (
                TransaksiIuranBulanan.objects.filter(
                    kompleks=warga.kompleks,
                    periode_bulan=periode_bulan,
                    periode_tahun=periode_tahun,
                )
                .exclude(status="REJECTED")
                .exists()
            )

            if existing:
                return Response(
                    {
                        "error": "Pembayaran untuk periode tersebut sudah tercatat atau sedang menunggu persetujuan."
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            iuran = TransaksiIuranBulanan.objects.create(
                kompleks=warga.kompleks,
                periode_bulan=periode_bulan,
                periode_tahun=periode_tahun,
                total_bayar=total_bayar,
                bukti_bayar=bukti_bayar,
                keterangan=keterangan,
                status="PENDING",
            )
            serializer = IuranRequestSerializer(iuran)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        if not warga.kompleks:
            return Response([])

        queryset = TransaksiIuranBulanan.objects.filter(
            kompleks=warga.kompleks
        ).order_by("-periode_tahun", "-periode_bulan")
        serializer = IuranRequestSerializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["post"], url_path="search")
    def search(self, request, *args, **kwargs):
        if request.method == "POST":
            search_term = request.data.get("search", "")
            queryset = search_warga_queryset(
                self.queryset,
                search_term,
                include_kompleks_fields_in_general_search=True,
            )
            logger.info(f"search to warga models with keyword {search_term}")
        else:
            queryset = self.queryset
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class iuranViewSet(viewsets.ModelViewSet):
    queryset = TransaksiIuranBulanan.objects.order_by("id")
    serializer_class = iuranSerializer
    permission_classes = [IsAuthenticated, IsAdminOrPetugas]


class kompleksViewSet(viewsets.ModelViewSet):
    queryset = Kompleks.objects.order_by("id")
    serializer_class = kompleksSerializer
    permission_classes = [IsAuthenticated, IsAdminOrPetugas]
    parser_classes = (MultiPartParser, FormParser, JSONParser)

    @action(detail=False, methods=["post"], url_path="search")
    def search(self, request, *args, **kwargs):
        if request.method == "POST":
            search_term = request.data.get("search", "")
            queryset = search_kompleks_queryset(self.queryset, search_term)
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
                    queryset = Warga.objects.filter(kompleks=idkompleks).exclude(
                        status_tinggal__in=["PINDAH", "MENINGGAL"]
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
            if request.content_type == "application/json":
                data = request.data
            else:
                data = request.POST

            search_term = data.get("blok_no", "")
            try:
                tahun = int(data.get("tahun", 0))
            except (TypeError, ValueError):
                return Response(
                    {"error": "Invalid year"}, status=status.HTTP_400_BAD_REQUEST
                )

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

        try:
            payment = record_iuran_payment(
                blok_no=search_term,
                periode_bulan=periode_bulan,
                periode_tahun=periode_tahun,
                total_bayar=total_bayar,
                bukti_bayar=bukti_bayar,
            )
            serializer = iuranSerializer(payment)
            return Response(serializer.data)
        except DatawargaError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Failed to record payment: {str(e)}")
            return Response(
                {"error": "Gagal mencatat pembayaran"},
                status=status.HTTP_400_BAD_REQUEST,
            )
