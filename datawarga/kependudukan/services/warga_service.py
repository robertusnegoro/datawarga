import logging
from typing import Dict, Any, Tuple
import uuid
from datetime import timedelta
from django.db import transaction
from django.contrib.auth.models import User
from django.utils import timezone
from django.urls import reverse
from kependudukan.errors import ValidationError
from kependudukan.models import (
    Warga,
    UserInvitation,
    WargaUpdateRequest,
    Surat,
    TransaksiIuranBulanan,
    Kendaraan,
    Penandatangan,
)
from kependudukan.selectors.warga_selector import get_warga_by_id
from kependudukan.ai.ai_service import get_ai_provider
from kependudukan.ai.ai_utils import optimize_image

logger = logging.getLogger(__name__)


def assign_kepala_keluarga(warga_id: int) -> Warga:
    """
    Sets the specified Warga as the head of the household (kepala_keluarga)
    and removes the flag from all other members in the same kompleks.
    """
    warga_record = get_warga_by_id(warga_id)
    if not warga_record.kompleks:
        return warga_record

    with transaction.atomic():
        # Unset others in the same complex
        warga_serumah = Warga.objects.filter(kompleks=warga_record.kompleks)
        for w in warga_serumah:
            if w.kepala_keluarga:
                w.kepala_keluarga = False
                w.save(update_fields=["kepala_keluarga"])

        # Set the selected one
        warga_record.kepala_keluarga = True
        warga_record.save(update_fields=["kepala_keluarga"])

    return warga_record


def process_ktp_scan(
    image_bytes: bytes, correlation_id: str
) -> Tuple[bool, str, Dict[str, Any], bool, str]:
    """
    Process a KTP image and return the extracted data.
    Returns: (success, status_message, extracted_data, quota_warning, quota_message)
    """
    try:
        optimized_bytes = optimize_image(image_bytes)
        logger.info(
            f"[SCAN_KTP_OPTIMIZE] [CorrelationID: {correlation_id}] Optimized size: {len(optimized_bytes)} bytes (Original: {len(image_bytes)} bytes)"
        )
    except Exception as e:
        logger.error(
            f"[SCAN_KTP_OPTIMIZE_FAIL] [CorrelationID: {correlation_id}] Image optimization failed: {str(e)}",
            exc_info=True,
        )
        return False, f"Gagal mengoptimalkan gambar KTP: {str(e)}", {}, False, ""

    try:
        provider = get_ai_provider()
        extracted_data = provider.extract_ktp_data(
            optimized_bytes, correlation_id=correlation_id
        )

        success_fields = []
        failed_fields = []

        fields_to_check = [
            "nama_lengkap",
            "nik",
            "alamat_ktp",
            "jenis_kelamin",
            "agama",
            "tempat_lahir",
            "tanggal_lahir",
        ]

        for field in fields_to_check:
            if extracted_data.get(field):
                success_fields.append(field)
            else:
                failed_fields.append(field)

        field_labels = {
            "nama_lengkap": "Nama",
            "nik": "NIK",
            "alamat_ktp": "Alamat",
            "jenis_kelamin": "Jenis Kelamin",
            "agama": "Agama",
            "tempat_lahir": "Tempat Lahir",
            "tanggal_lahir": "Tanggal Lahir",
        }

        success_labels = [field_labels[f] for f in success_fields]
        failed_labels = [field_labels[f] for f in failed_fields]

        status_message = "Scan KTP selesai."
        if success_labels:
            status_message += f" Berhasil mengenali: {', '.join(success_labels)}."
        if failed_labels:
            status_message += f" Gagal mengenali: {', '.join(failed_labels)}."

        quota_warning = False
        quota_message = ""
        try:
            if provider.is_quota_low(correlation_id=correlation_id):
                quota_warning = True
                remaining = provider.get_remaining_quota(correlation_id=correlation_id)
                quota_message = f"Peringatan: Kuota penyedia AI hampir habis (Sisa kuota: {remaining if remaining is not None else 'rendah'})."
        except Exception as q_err:
            logger.warning(
                f"[SCAN_KTP_QUOTA_ERROR] Could not check quota: {str(q_err)}"
            )

        logger.info(
            f"[SCAN_KTP_SUCCESS] [CorrelationID: {correlation_id}] Fields extracted: {success_fields}, Quota warning: {quota_warning}"
        )

        return True, status_message, extracted_data, quota_warning, quota_message

    except Exception as e:
        logger.error(f"[SCAN_KTP_PROCESS_ERROR] {str(e)}", exc_info=True)
        return (
            False,
            f"Terjadi kesalahan saat memproses gambar KTP: {str(e)}",
            {},
            False,
            "",
        )


def create_warga_invitation(warga_id: int, email: str, request) -> str:
    """
    Creates an inactive User, links it to Warga, creates UserInvitation,
    and returns the activation/invitation link.
    """
    warga = Warga.objects.get(pk=warga_id)
    try:
        if warga.user is not None:
            raise ValidationError("Warga ini sudah memiliki akun login.")
    except AttributeError:
        pass

    # Check if a user with this email already exists
    if User.objects.filter(email__iexact=email).exists():
        raise ValidationError("Email ini sudah digunakan oleh akun lain.")

    with transaction.atomic():
        # Create user (inactive)
        username = email.lower()
        user = User.objects.create(
            username=username,
            email=email,
            first_name=warga.nama_lengkap[:30],
            is_active=False,
        )

        warga.user = user
        warga.save()

        # Create invitation link
        token = uuid.uuid4().hex
        expires_at = timezone.now() + timedelta(days=1)
        UserInvitation.objects.create(
            user=user, token=token, expires_at=expires_at, is_used=False
        )

    # Construct the full invitation url
    activation_path = reverse("kependudukan:user_activate", kwargs={"token": token})
    activation_link = request.build_absolute_uri(activation_path)

    logger.info(f"Created warga invitation for warga_id={warga_id}, token={token}")
    return activation_link


def submit_warga_update_request(
    warga: Warga, fields_data: dict, files: dict = None,
    requested_by: Warga = None, is_new_warga: bool = False, kompleks=None
) -> WargaUpdateRequest:
    """
    Saves warga change requests in WargaUpdateRequest to await admin approval.
    """
    files = files or {}
    req = WargaUpdateRequest(
        warga=warga,
        requested_by=requested_by,
        is_new_warga=is_new_warga,
        kompleks=kompleks,
        data_changes=fields_data,
        status="PENDING",
        foto_path=files.get("foto_path"),
        ktp_image_path=files.get("ktp_image_path"),
    )
    req.save()
    logger.info(f"Submitted profile update request {req.id} for warga {warga.id if warga else 'NEW'}")
    return req


def approve_warga_update_request(
    update_request_id: int, admin_user
) -> WargaUpdateRequest:
    """
    Applies the changes stored in WargaUpdateRequest to the Warga model and marks it APPROVED.
    """
    req = WargaUpdateRequest.objects.get(pk=update_request_id)
    if req.status != "PENDING":
        raise ValidationError("Request update ini sudah diproses.")

    with transaction.atomic():
        if req.is_new_warga:
            warga = Warga(kompleks=req.kompleks)
        else:
            warga = req.warga

        # Update simple fields
        for field, val in req.data_changes.items():
            if hasattr(warga, field) and field not in ["id", "user"]:
                setattr(warga, field, val)

        # Update file fields if present
        if req.foto_path:
            warga.foto_path = req.foto_path
        if req.ktp_image_path:
            warga.ktp_image_path = req.ktp_image_path

        warga.save()

        if req.is_new_warga:
            req.warga = warga

        req.status = "APPROVED"
        req.notes = f"Disetujui oleh {admin_user.username}"
        req.save()

    logger.info(
        f"Approved update request {req.id} for warga {warga.id} by admin {admin_user.username}"
    )
    return req


def reject_warga_update_request(
    update_request_id: int, admin_user, reason: str
) -> WargaUpdateRequest:
    """
    Marks update request as REJECTED with notes.
    """
    req = WargaUpdateRequest.objects.get(pk=update_request_id)
    if req.status != "PENDING":
        raise ValidationError("Request update ini sudah diproses.")

    req.status = "REJECTED"
    req.notes = f"Ditolak oleh {admin_user.username}. Alasan: {reason}"
    req.save()
    logger.info(f"Rejected update request {req.id} by admin {admin_user.username}")
    return req


def approve_surat(
    surat_id: int, admin_user, nomor_surat: str = None, penandatangan_id: int = None
) -> Surat:
    """
    Approves document request (Surat).
    """
    surat = Surat.objects.get(pk=surat_id)
    if surat.status != "PENDING":
        raise ValidationError("Surat ini sudah diproses.")

    surat.status = "APPROVED"
    if nomor_surat:
        surat.nomor_surat = nomor_surat
    if penandatangan_id:
        surat.penandatangan = Penandatangan.objects.get(pk=penandatangan_id)
    surat.keterangan_status = f"Disetujui oleh {admin_user.username}"
    surat.save()
    logger.info(f"Approved surat {surat_id} by admin {admin_user.username}")
    return surat


def reject_surat(surat_id: int, admin_user, reason: str) -> Surat:
    """
    Rejects document request (Surat).
    """
    surat = Surat.objects.get(pk=surat_id)
    if surat.status != "PENDING":
        raise ValidationError("Surat ini sudah diproses.")

    surat.status = "REJECTED"
    surat.keterangan_status = f"Ditolak oleh {admin_user.username}. Alasan: {reason}"
    surat.save()
    logger.info(f"Rejected surat {surat_id} by admin {admin_user.username}")
    return surat


def approve_iuran(iuran_id: int, admin_user) -> TransaksiIuranBulanan:
    """
    Approves monthly iuran payment proof (Triggers KasTransaksi creation signal).
    """
    iuran = TransaksiIuranBulanan.objects.get(pk=iuran_id)
    if iuran.status != "PENDING":
        raise ValidationError("Pembayaran iuran ini sudah diproses.")

    iuran.status = "APPROVED"
    iuran.keterangan_status = f"Disetujui oleh {admin_user.username}"
    iuran.save()
    logger.info(f"Approved iuran {iuran_id} by admin {admin_user.username}")
    return iuran


def reject_iuran(iuran_id: int, admin_user, reason: str) -> TransaksiIuranBulanan:
    """
    Rejects monthly iuran payment.
    """
    iuran = TransaksiIuranBulanan.objects.get(pk=iuran_id)
    if iuran.status != "PENDING":
        raise ValidationError("Pembayaran iuran ini sudah diproses.")

    iuran.status = "REJECTED"
    iuran.keterangan_status = f"Ditolak oleh {admin_user.username}. Alasan: {reason}"
    iuran.save()
    logger.info(f"Rejected iuran {iuran_id} by admin {admin_user.username}")
    return iuran


def approve_kendaraan(kendaraan_id: int, admin_user) -> Kendaraan:
    """
    Approves vehicle registration.
    """
    kendaraan = Kendaraan.objects.get(pk=kendaraan_id)
    if kendaraan.status != "PENDING":
        raise ValidationError("Registrasi kendaraan ini sudah diproses.")

    kendaraan.status = "APPROVED"
    kendaraan.keterangan_status = f"Disetujui oleh {admin_user.username}"
    kendaraan.save()
    logger.info(f"Approved kendaraan {kendaraan_id} by admin {admin_user.username}")
    return kendaraan


def reject_kendaraan(kendaraan_id: int, admin_user, reason: str) -> Kendaraan:
    """
    Rejects vehicle registration.
    """
    kendaraan = Kendaraan.objects.get(pk=kendaraan_id)
    if kendaraan.status != "PENDING":
        raise ValidationError("Registrasi kendaraan ini sudah diproses.")

    kendaraan.status = "REJECTED"
    kendaraan.keterangan_status = (
        f"Ditolak oleh {admin_user.username}. Alasan: {reason}"
    )
    kendaraan.save()
    logger.info(f"Rejected kendaraan {kendaraan_id} by admin {admin_user.username}")
    return kendaraan
