import logging
import uuid

import base64
import io
import time
import pyotp
import qrcode

from rest_framework import status, viewsets, serializers
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from kependudukan.errors import DatawargaError
from kependudukan.models import (
    Warga,
    Kompleks,
    TransaksiIuranBulanan,
    WargaUpdateRequest,
    Surat,
    Kendaraan,
    Penandatangan,
)
from kependudukan.selectors.kompleks_selector import search_kompleks_queryset
from kependudukan.selectors.warga_selector import search_warga_queryset
from kependudukan.serializers import (
    wargaSerializer,
    kompleksSerializer,
    iuranSerializer,
    KtpScanRequestSerializer,
    UserProfileDetailSerializer,
    ChangePasswordSerializer,
    MfaEnableSerializer,
    MfaDisableSerializer,
    CustomTokenObtainPairSerializer,
    SuratRequestSerializer,
    KendaraanRequestSerializer,
    IuranRequestSerializer,
    WargaUpdateRequestSerializer,
    WargaMeUpdateRequestSerializer,
)
from rest_framework_simplejwt.views import TokenObtainPairView
from drf_yasg.utils import swagger_auto_schema
from kependudukan.services.iuran_service import record_iuran_payment
from kependudukan.services.warga_service import process_ktp_scan
from kependudukan.throttles import KtpScanRateThrottle
from kependudukan.utils.auth_guards import IsAdminOrPetugas

logger = logging.getLogger(__name__)


def _get_allowed_kompleks_queryset(user, queryset):
    """Helper to filter Kompleks queryset based on user permissions"""
    if user.is_superuser:
        return queryset
    try:
        from kependudukan.models import UserPermission

        perm = UserPermission.objects.get(user=user)
        if str(perm.permission_group).lower() != "all":
            return queryset.filter(permission_group=perm.permission_group)
    except Exception:
        pass
    return queryset


def _get_allowed_warga_queryset(user, queryset):
    """Helper to filter Warga queryset based on user permissions"""
    if user.is_superuser:
        return queryset
    try:
        from kependudukan.models import UserPermission

        perm = UserPermission.objects.get(user=user)
        if str(perm.permission_group).lower() != "all":
            return queryset.filter(kompleks__permission_group=perm.permission_group)
    except Exception:
        pass
    return queryset


def _get_allowed_iuran_queryset(user, queryset):
    """Helper to filter Iuran queryset based on user permissions"""
    if user.is_superuser:
        return queryset
    try:
        from kependudukan.models import UserPermission

        perm = UserPermission.objects.get(user=user)
        if str(perm.permission_group).lower() != "all":
            return queryset.filter(kompleks__permission_group=perm.permission_group)
    except Exception:
        pass
    return queryset


class wargaViewSet(viewsets.ModelViewSet):
    queryset = Warga.objects.order_by("id")
    serializer_class = wargaSerializer
    permission_classes = [IsAuthenticated, IsAdminOrPetugas]

    def get_queryset(self):
        user = self.request.user
        queryset = super().get_queryset()
        if self.action in [
            "me",
            "me_update",
            "me_requests",
            "me_surat",
            "me_kendaraan",
            "me_iuran",
            "choices",
        ]:
            return queryset
        return _get_allowed_warga_queryset(user, queryset)

    def get_permissions(self):
        if self.action in [
            "me",
            "me_update",
            "me_requests",
            "me_surat",
            "me_kendaraan",
            "me_iuran",
            "choices",
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

    @swagger_auto_schema(
        request_body=WargaMeUpdateRequestSerializer,
        responses={201: WargaUpdateRequestSerializer},
        operation_description="Ajukan perubahan data warga (atau pembuatan warga baru dalam satu kompleks).",
    )
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
                if not (
                    target_warga == warga
                    or (warga.kompleks and target_warga.kompleks == warga.kompleks)
                ):
                    return Response(
                        {
                            "error": "Target warga tidak valid atau tidak berada dalam satu rumah."
                        },
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

        update_request = submit_warga_update_request(
            warga=target_warga,
            fields_data=changes,
            files=files,
            requested_by=warga,
            is_new_warga=is_new_warga,
            kompleks=warga.kompleks,
        )
        serializer = WargaUpdateRequestSerializer(update_request)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @swagger_auto_schema(
        responses={200: WargaUpdateRequestSerializer(many=True)},
        operation_description="Dapatkan daftar riwayat pengajuan perubahan data warga.",
    )
    @action(detail=False, methods=["get"], url_path="me/requests")
    def me_requests(self, request):
        warga = self._get_warga(request)
        from kependudukan.models import WargaUpdateRequest
        from django.db.models import Q

        queryset = (
            WargaUpdateRequest.objects.filter(Q(warga=warga) | Q(requested_by=warga))
            .distinct()
            .order_by("-created_at")
        )
        serializer = WargaUpdateRequestSerializer(queryset, many=True)
        return Response(serializer.data)

    @swagger_auto_schema(
        method="get",
        responses={200: SuratRequestSerializer(many=True)},
        operation_description="Dapatkan daftar permohonan surat milik warga aktif.",
    )
    @swagger_auto_schema(
        method="post",
        request_body=SuratRequestSerializer,
        responses={201: SuratRequestSerializer},
        operation_description="Ajukan permohonan surat baru.",
    )
    @action(detail=False, methods=["get", "post"], url_path="me/surat")
    def me_surat(self, request):
        warga = self._get_warga(request)
        from kependudukan.models import Surat

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

    @swagger_auto_schema(
        method="get",
        responses={200: KendaraanRequestSerializer(many=True)},
        operation_description="Dapatkan daftar kendaraan terdaftar milik warga aktif.",
    )
    @swagger_auto_schema(
        method="post",
        request_body=KendaraanRequestSerializer,
        responses={201: KendaraanRequestSerializer},
        operation_description="Daftarkan kendaraan baru.",
    )
    @action(detail=False, methods=["get", "post"], url_path="me/kendaraan")
    def me_kendaraan(self, request):
        warga = self._get_warga(request)
        from kependudukan.models import Kendaraan

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

    @swagger_auto_schema(
        method="get",
        responses={200: IuranRequestSerializer(many=True)},
        operation_description="Dapatkan daftar pembayaran iuran bulanan untuk kompleks warga aktif.",
    )
    @swagger_auto_schema(
        method="post",
        request_body=IuranRequestSerializer,
        responses={201: IuranRequestSerializer},
        operation_description="Unggah bukti pembayaran iuran bulanan baru.",
    )
    @action(
        detail=False,
        methods=["get", "post"],
        url_path="me/iuran",
        parser_classes=(MultiPartParser, FormParser, JSONParser),
    )
    def me_iuran(self, request):
        warga = self._get_warga(request)
        from kependudukan.models import TransaksiIuranBulanan

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

    @swagger_auto_schema(
        request_body=KtpScanRequestSerializer,
        responses={
            200: "Successfully scanned KTP",
            400: "Invalid file or parameters",
            500: "Internal server/AI error",
        },
    )
    @action(
        detail=False,
        methods=["post"],
        url_path="scan-ktp",
        parser_classes=(MultiPartParser, FormParser),
        throttle_classes=[KtpScanRateThrottle],
    )
    def scan_ktp(self, request):
        """AI-powered KTP field recognition.

        Accepts a KTP image and returns extracted fields
        (NIK, nama, alamat, jenis_kelamin, agama, tempat_lahir, tanggal_lahir).
        """
        correlation_id = str(uuid.uuid4())
        logger.info(
            "[API_SCAN_KTP_START] [CorrelationID: %s] User: %s",
            correlation_id,
            request.user.username,
        )

        ktp_file = request.FILES.get("ktp_image")
        if not ktp_file:
            logger.warning(
                "[API_SCAN_KTP_FAIL] [CorrelationID: %s] No ktp_image file provided",
                correlation_id,
            )
            return Response(
                {
                    "success": False,
                    "message": "File foto KTP (ktp_image) harus dilampirkan.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        image_bytes = ktp_file.read()
        logger.info(
            "[API_SCAN_KTP_IMAGE] [CorrelationID: %s] File: %s, Size: %d bytes",
            correlation_id,
            ktp_file.name,
            len(image_bytes),
        )

        success, msg, extracted_data, quota_warning, quota_message = process_ktp_scan(
            image_bytes, correlation_id
        )

        if success:
            logger.info(
                "[API_SCAN_KTP_SUCCESS] [CorrelationID: %s] Duration: completed",
                correlation_id,
            )
            return Response(
                {
                    "success": True,
                    "data": extracted_data,
                    "message": msg,
                    "quota_warning": quota_warning,
                    "quota_message": quota_message,
                },
                status=status.HTTP_200_OK,
            )

        logger.error(
            "[API_SCAN_KTP_FAIL] [CorrelationID: %s] Error: %s",
            correlation_id,
            msg,
        )
        return Response(
            {"success": False, "message": msg},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    @action(detail=False, methods=["post"], url_path="search")
    def search(self, request, *args, **kwargs):
        if request.method == "POST":
            search_term = request.data.get("search", "")
            queryset = search_warga_queryset(
                self.get_queryset(),
                search_term,
                include_kompleks_fields_in_general_search=True,
            )
            logger.info(f"search to warga models with keyword {search_term}")
        else:
            queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"], url_path="choices")
    def choices(self, request):
        correlation_id = str(uuid.uuid4())
        user = request.user
        start_time = time.time()

        logger.info(
            "Operation started",
            extra={
                "operation": "warga_get_choices",
                "userId": user.id,
                "correlationId": correlation_id,
            },
        )

        try:
            data = {
                "status_keluarga": [
                    {"value": choice[0], "label": choice[1]}
                    for choice in Warga.STATUS_KELUARGA
                ],
                "agama": [
                    {"value": choice[0], "label": choice[1]}
                    for choice in Warga.RELIGIONS
                ],
                "pekerjaan": [
                    {"value": choice[0], "label": choice[1]}
                    for choice in Warga.PEKERJAAN
                ],
                "status_kawin": [
                    {"value": choice[0], "label": choice[1]}
                    for choice in Warga.STATUS_KAWIN
                ],
                "status_tinggal": [
                    {"value": choice[0], "label": choice[1]}
                    for choice in Warga.STATUS_TINGGAL
                ],
                "jenis_kelamin": [
                    {"value": choice[0], "label": choice[1]}
                    for choice in Warga.JENIS_KELAMIN
                ],
            }
            duration = int((time.time() - start_time) * 1000)
            logger.info(
                "Operation success",
                extra={
                    "operation": "warga_get_choices",
                    "userId": user.id,
                    "correlationId": correlation_id,
                    "duration": duration,
                },
            )
            return Response(data)
        except Exception as e:
            duration = int((time.time() - start_time) * 1000)
            logger.error(
                "Operation failure",
                extra={
                    "operation": "warga_get_choices",
                    "userId": user.id,
                    "correlationId": correlation_id,
                    "duration": duration,
                    "error": str(e),
                },
            )
            return Response(
                {"error": "Gagal mengambil data pilihan."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class iuranViewSet(viewsets.ModelViewSet):
    queryset = TransaksiIuranBulanan.objects.order_by("id")
    serializer_class = iuranSerializer
    permission_classes = [IsAuthenticated, IsAdminOrPetugas]

    def get_queryset(self):
        queryset = _get_allowed_iuran_queryset(
            self.request.user, super().get_queryset()
        )
        status_param = self.request.query_params.get("status")
        if status_param:
            queryset = queryset.filter(status=status_param.upper())
        return queryset

    @action(detail=True, methods=["post"], url_path="approve")
    def approve(self, request, pk=None):
        from kependudukan.services.warga_service import approve_iuran
        from kependudukan.errors import ValidationError

        try:
            iuran = approve_iuran(pk, request.user)
            return Response(self.get_serializer(iuran).data)
        except ValidationError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=["post"], url_path="reject")
    def reject(self, request, pk=None):
        from kependudukan.services.warga_service import reject_iuran
        from kependudukan.errors import ValidationError

        reason = request.data.get("reason", "").strip()
        if not reason:
            return Response(
                {"error": "Alasan penolakan harus diisi."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            iuran = reject_iuran(pk, request.user, reason)
            return Response(self.get_serializer(iuran).data)
        except ValidationError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class kompleksViewSet(viewsets.ModelViewSet):
    queryset = Kompleks.objects.order_by("id")
    serializer_class = kompleksSerializer
    permission_classes = [IsAuthenticated, IsAdminOrPetugas]
    parser_classes = (MultiPartParser, FormParser, JSONParser)

    def get_queryset(self):
        return _get_allowed_kompleks_queryset(self.request.user, super().get_queryset())

    @action(detail=False, methods=["post"], url_path="search")
    def search(self, request, *args, **kwargs):
        if request.method == "POST":
            search_term = request.data.get("search", "")
            queryset = search_kompleks_queryset(self.get_queryset(), search_term)
            logger.info(f"search to kompleks models with keyword {search_term}")
        else:
            queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["post"], url_path="warga")
    def warga(self, request, *args, **kwargs):
        queryset = Warga.objects.none()  # Initialize with empty queryset

        if request.method == "POST":
            search_term = request.data.get("blok_no", "")

            if "/" in search_term:
                split_keyword = search_term.split("/")
                data_kompleks = self.get_queryset().filter(
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
                data_kompleks = self.get_queryset().filter(
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

        if "/" in search_term:
            split_keyword = search_term.split("/")
            data_kompleks = (
                self.get_queryset()
                .filter(
                    blok__icontains=split_keyword[0].strip(),
                    nomor=split_keyword[1].strip(),
                )
                .first()
            )
            if not data_kompleks:
                return Response(
                    {
                        "error": "Kompleks tidak ditemukan atau Anda tidak memiliki akses."
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
        else:
            return Response(
                {"error": "Format blok_no tidak valid."},
                status=status.HTTP_400_BAD_REQUEST,
            )

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


class UserProfileViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]
    parser_classes = (MultiPartParser, FormParser, JSONParser)

    def list(self, request):
        correlation_id = str(uuid.uuid4())
        user = request.user
        start_time = time.time()

        logger.info(
            "Operation started",
            extra={
                "operation": "get_profile",
                "userId": user.id,
                "correlationId": correlation_id,
            },
        )

        serializer = UserProfileDetailSerializer(user, context={"request": request})

        duration = int((time.time() - start_time) * 1000)
        logger.info(
            "Operation success",
            extra={
                "operation": "get_profile",
                "userId": user.id,
                "correlationId": correlation_id,
                "duration": duration,
            },
        )
        return Response(serializer.data)

    @action(detail=False, methods=["put", "patch"], url_path="update")
    def update_profile(self, request):
        correlation_id = str(uuid.uuid4())
        user = request.user
        start_time = time.time()

        logger.info(
            "Operation started",
            extra={
                "operation": "update_profile_api",
                "userId": user.id,
                "correlationId": correlation_id,
            },
        )

        serializer = UserProfileDetailSerializer(
            user,
            data=request.data,
            partial=(request.method == "PATCH"),
            context={"request": request},
        )

        if serializer.is_valid():
            serializer.save()
            duration = int((time.time() - start_time) * 1000)
            logger.info(
                "Operation success",
                extra={
                    "operation": "update_profile_api",
                    "userId": user.id,
                    "correlationId": correlation_id,
                    "duration": duration,
                },
            )
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            duration = int((time.time() - start_time) * 1000)
            logger.error(
                "Operation failure",
                extra={
                    "operation": "update_profile_api",
                    "userId": user.id,
                    "correlationId": correlation_id,
                    "duration": duration,
                    "error": str(serializer.errors),
                },
            )
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=["post"], url_path="change-password")
    def change_password(self, request):
        correlation_id = str(uuid.uuid4())
        user = request.user
        start_time = time.time()

        logger.info(
            "Operation started",
            extra={
                "operation": "change_password_api",
                "userId": user.id,
                "correlationId": correlation_id,
            },
        )

        serializer = ChangePasswordSerializer(
            data=request.data, context={"request": request}
        )
        if serializer.is_valid():
            user.set_password(serializer.validated_data["new_password"])
            user.save()

            from django.contrib.auth import update_session_auth_hash

            update_session_auth_hash(request, user)

            duration = int((time.time() - start_time) * 1000)
            logger.info(
                "Operation success",
                extra={
                    "operation": "change_password_api",
                    "userId": user.id,
                    "correlationId": correlation_id,
                    "duration": duration,
                },
            )
            return Response(
                {"message": "Kata sandi Anda berhasil diperbarui."},
                status=status.HTTP_200_OK,
            )
        else:
            duration = int((time.time() - start_time) * 1000)
            logger.error(
                "Operation failure",
                extra={
                    "operation": "change_password_api",
                    "userId": user.id,
                    "correlationId": correlation_id,
                    "duration": duration,
                    "error": str(serializer.errors),
                },
            )
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=["post"], url_path="mfa/setup")
    def mfa_setup(self, request):
        correlation_id = str(uuid.uuid4())
        user = request.user
        start_time = time.time()

        logger.info(
            "Operation started",
            extra={
                "operation": "mfa_setup_api",
                "userId": user.id,
                "correlationId": correlation_id,
            },
        )

        profile = user.profile
        if profile.mfa_enabled:
            duration = int((time.time() - start_time) * 1000)
            logger.warning(
                "Operation failure: MFA already enabled",
                extra={
                    "operation": "mfa_setup_api",
                    "userId": user.id,
                    "correlationId": correlation_id,
                    "duration": duration,
                    "error": "MFA is already enabled",
                },
            )
            return Response(
                {"error": "MFA sudah aktif pada akun Anda."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        temp_secret = pyotp.random_base32()
        totp = pyotp.TOTP(temp_secret)
        provisioning_uri = totp.provisioning_uri(
            name=user.username, issuer_name="DataWarga"
        )

        qr = qrcode.QRCode(version=1, box_size=5, border=3)
        qr.add_data(provisioning_uri)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")

        buffered = io.BytesIO()
        img.save(buffered, format="PNG")
        qr_base64 = base64.b64encode(buffered.getvalue()).decode()

        duration = int((time.time() - start_time) * 1000)
        logger.info(
            "Operation success",
            extra={
                "operation": "mfa_setup_api",
                "userId": user.id,
                "correlationId": correlation_id,
                "duration": duration,
            },
        )
        return Response(
            {
                "secret_key": temp_secret,
                "provisioning_uri": provisioning_uri,
                "qr_base64": qr_base64,
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=["post"], url_path="mfa/enable")
    def mfa_enable(self, request):
        correlation_id = str(uuid.uuid4())
        user = request.user
        start_time = time.time()

        logger.info(
            "Operation started",
            extra={
                "operation": "mfa_enable_api",
                "userId": user.id,
                "correlationId": correlation_id,
            },
        )

        profile = user.profile
        if profile.mfa_enabled:
            duration = int((time.time() - start_time) * 1000)
            logger.warning(
                "Operation failure: MFA already enabled",
                extra={
                    "operation": "mfa_enable_api",
                    "userId": user.id,
                    "correlationId": correlation_id,
                    "duration": duration,
                    "error": "MFA is already enabled",
                },
            )
            return Response(
                {"error": "MFA sudah aktif pada akun Anda."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = MfaEnableSerializer(data=request.data)
        if serializer.is_valid():
            secret_key = serializer.validated_data["secret_key"]
            token = serializer.validated_data["token"].strip()

            totp = pyotp.TOTP(secret_key)
            if totp.verify(token):
                profile.totp_secret = secret_key
                profile.mfa_enabled = True
                profile.save()

                duration = int((time.time() - start_time) * 1000)
                logger.info(
                    "Operation success",
                    extra={
                        "operation": "mfa_enable_api",
                        "userId": user.id,
                        "correlationId": correlation_id,
                        "duration": duration,
                    },
                )
                return Response(
                    {
                        "message": "Multi-Factor Authentication (MFA) berhasil diaktifkan."
                    },
                    status=status.HTTP_200_OK,
                )
            else:
                duration = int((time.time() - start_time) * 1000)
                logger.warning(
                    "Operation failure: invalid token for setup verification",
                    extra={
                        "operation": "mfa_enable_api",
                        "userId": user.id,
                        "correlationId": correlation_id,
                        "duration": duration,
                        "error": "Invalid verification token supplied during setup",
                    },
                )
                return Response(
                    {"token": ["Kode verification salah. Silakan coba lagi."]},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        else:
            duration = int((time.time() - start_time) * 1000)
            logger.error(
                "Operation failure",
                extra={
                    "operation": "mfa_enable_api",
                    "userId": user.id,
                    "correlationId": correlation_id,
                    "duration": duration,
                    "error": str(serializer.errors),
                },
            )
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=["post"], url_path="mfa/disable")
    def mfa_disable(self, request):
        correlation_id = str(uuid.uuid4())
        user = request.user
        start_time = time.time()

        logger.info(
            "Operation started",
            extra={
                "operation": "mfa_disable_api",
                "userId": user.id,
                "correlationId": correlation_id,
            },
        )

        profile = user.profile
        if not profile.mfa_enabled:
            duration = int((time.time() - start_time) * 1000)
            logger.warning(
                "Operation failure: MFA is not enabled",
                extra={
                    "operation": "mfa_disable_api",
                    "userId": user.id,
                    "correlationId": correlation_id,
                    "duration": duration,
                    "error": "MFA is not enabled",
                },
            )
            return Response(
                {"error": "MFA tidak aktif pada akun Anda."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = MfaDisableSerializer(data=request.data)
        if serializer.is_valid():
            token = serializer.validated_data["token"].strip()

            totp = pyotp.TOTP(profile.totp_secret)
            if totp.verify(token):
                profile.mfa_enabled = False
                profile.totp_secret = None
                profile.save()

                duration = int((time.time() - start_time) * 1000)
                logger.info(
                    "Operation success",
                    extra={
                        "operation": "mfa_disable_api",
                        "userId": user.id,
                        "correlationId": correlation_id,
                        "duration": duration,
                    },
                )
                return Response(
                    {
                        "message": "Multi-Factor Authentication (MFA) berhasil dinonaktifkan."
                    },
                    status=status.HTTP_200_OK,
                )
            else:
                duration = int((time.time() - start_time) * 1000)
                logger.warning(
                    "Operation failure: invalid token for disabling MFA",
                    extra={
                        "operation": "mfa_disable_api",
                        "userId": user.id,
                        "correlationId": correlation_id,
                        "duration": duration,
                        "error": "Invalid verification token supplied during disable attempt",
                    },
                )
                return Response(
                    {"token": ["Kode verification salah. Silakan coba lagi."]},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        else:
            duration = int((time.time() - start_time) * 1000)
            logger.error(
                "Operation failure",
                extra={
                    "operation": "mfa_disable_api",
                    "userId": user.id,
                    "correlationId": correlation_id,
                    "duration": duration,
                    "error": str(serializer.errors),
                },
            )
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer


class WargaUpdateRequestViewSet(viewsets.ModelViewSet):
    queryset = WargaUpdateRequest.objects.all().order_by("-created_at")
    serializer_class = WargaUpdateRequestSerializer
    permission_classes = [IsAuthenticated, IsAdminOrPetugas]

    def get_queryset(self):
        queryset = super().get_queryset()
        status_param = self.request.query_params.get("status")
        if status_param:
            queryset = queryset.filter(status=status_param.upper())
        return queryset

    @action(detail=True, methods=["post"], url_path="approve")
    def approve(self, request, pk=None):
        from kependudukan.services.warga_service import approve_warga_update_request
        from kependudukan.errors import ValidationError

        try:
            update_req = approve_warga_update_request(pk, request.user)
            return Response(self.get_serializer(update_req).data)
        except ValidationError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=["post"], url_path="reject")
    def reject(self, request, pk=None):
        from kependudukan.services.warga_service import reject_warga_update_request
        from kependudukan.errors import ValidationError

        reason = request.data.get("reason", "").strip()
        if not reason:
            return Response(
                {"error": "Alasan penolakan harus diisi."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            update_req = reject_warga_update_request(pk, request.user, reason)
            return Response(self.get_serializer(update_req).data)
        except ValidationError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class AdminSuratViewSet(viewsets.ModelViewSet):
    queryset = Surat.objects.all().order_by("-tanggal_surat")
    serializer_class = SuratRequestSerializer
    permission_classes = [IsAuthenticated, IsAdminOrPetugas]

    def get_queryset(self):
        queryset = super().get_queryset()
        status_param = self.request.query_params.get("status")
        if status_param:
            queryset = queryset.filter(status=status_param.upper())
        return queryset

    @action(detail=True, methods=["post"], url_path="approve")
    def approve(self, request, pk=None):
        from kependudukan.services.warga_service import approve_surat
        from kependudukan.errors import ValidationError

        nomor_surat = request.data.get("nomor_surat", "").strip()
        penandatangan_id = request.data.get("penandatangan")
        if penandatangan_id:
            try:
                penandatangan_id = int(penandatangan_id)
            except ValueError:
                return Response(
                    {"error": "Penandatangan ID tidak valid."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        try:
            surat = approve_surat(pk, request.user, nomor_surat, penandatangan_id)
            return Response(self.get_serializer(surat).data)
        except ValidationError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=["post"], url_path="reject")
    def reject(self, request, pk=None):
        from kependudukan.services.warga_service import reject_surat
        from kependudukan.errors import ValidationError

        reason = request.data.get("reason", "").strip()
        if not reason:
            return Response(
                {"error": "Alasan penolakan harus diisi."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            surat = reject_surat(pk, request.user, reason)
            return Response(self.get_serializer(surat).data)
        except ValidationError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class AdminKendaraanViewSet(viewsets.ModelViewSet):
    queryset = Kendaraan.objects.all().order_by("-id")
    serializer_class = KendaraanRequestSerializer
    permission_classes = [IsAuthenticated, IsAdminOrPetugas]

    def get_queryset(self):
        queryset = super().get_queryset()
        status_param = self.request.query_params.get("status")
        if status_param:
            queryset = queryset.filter(status=status_param.upper())
        return queryset

    @action(detail=True, methods=["post"], url_path="approve")
    def approve(self, request, pk=None):
        from kependudukan.services.warga_service import approve_kendaraan
        from kependudukan.errors import ValidationError

        try:
            kendaraan = approve_kendaraan(pk, request.user)
            return Response(self.get_serializer(kendaraan).data)
        except ValidationError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=["post"], url_path="reject")
    def reject(self, request, pk=None):
        from kependudukan.services.warga_service import reject_kendaraan
        from kependudukan.errors import ValidationError

        reason = request.data.get("reason", "").strip()
        if not reason:
            return Response(
                {"error": "Alasan penolakan harus diisi."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            kendaraan = reject_kendaraan(pk, request.user, reason)
            return Response(self.get_serializer(kendaraan).data)
        except ValidationError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class PenandatanganSerializer(serializers.ModelSerializer):
    class Meta:
        model = Penandatangan
        fields = ["id", "nama", "jabatan", "aktif"]


class PenandatanganViewSet(viewsets.ModelViewSet):
    queryset = Penandatangan.objects.all().order_by("nama")
    serializer_class = PenandatanganSerializer
    permission_classes = [IsAuthenticated, IsAdminOrPetugas]


class AdminDashboardViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated, IsAdminOrPetugas]

    def list(self, request):
        from django.db.models import Sum
        from django.utils import timezone
        from kependudukan.models import (
            Kompleks,
            TransaksiIuranBulanan,
            Kendaraan,
            Surat,
            Warga,
            WargaUpdateRequest,
        )
        from kependudukan.serializers import (
            iuranSerializer,
            KendaraanRequestSerializer,
            SuratRequestSerializer,
            WargaUpdateRequestSerializer,
        )

        current_year = timezone.now().year

        # 1. Summary totals — use .count() directly on the full queryset so these
        #    are never affected by pagination settings.
        total_warga = Warga.objects.count()
        total_rumah = Kompleks.objects.count()

        # 2. Calculate current year total approved iuran income
        total_iuran = (
            TransaksiIuranBulanan.objects.filter(
                periode_tahun=current_year, status="APPROVED"
            ).aggregate(total=Sum("total_bayar"))["total"]
            or 0
        )

        # 3. Get pending querysets
        pending_iurans = TransaksiIuranBulanan.objects.filter(
            status="PENDING"
        ).order_by("id")
        pending_kendaraans = Kendaraan.objects.filter(status="PENDING").order_by("id")
        pending_surats = Surat.objects.filter(status="PENDING").order_by(
            "-tanggal_surat"
        )
        pending_warga_updates = WargaUpdateRequest.objects.filter(
            status="PENDING"
        ).order_by("-created_at")

        # 4. Calculate counts
        pending_counts = {
            "iuran": pending_iurans.count(),
            "kendaraan": pending_kendaraans.count(),
            "surat": pending_surats.count(),
            "warga_updates": pending_warga_updates.count(),
        }

        # 5. Serialize pending lists
        context = {"request": request}
        pending_list = {
            "iuran": iuranSerializer(pending_iurans, many=True, context=context).data,
            "kendaraan": KendaraanRequestSerializer(
                pending_kendaraans, many=True, context=context
            ).data,
            "surat": SuratRequestSerializer(
                pending_surats, many=True, context=context
            ).data,
            "warga_updates": WargaUpdateRequestSerializer(
                pending_warga_updates, many=True, context=context
            ).data,
        }

        return Response(
            {
                "total_warga": total_warga,
                "total_rumah": total_rumah,
                "total_iuran_current_year": total_iuran,
                "pending_counts": pending_counts,
                "pending_list": pending_list,
            }
        )
