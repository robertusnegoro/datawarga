import logging
from typing import Dict, Any, Tuple
from django.db import transaction
from kependudukan.models import Warga
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
