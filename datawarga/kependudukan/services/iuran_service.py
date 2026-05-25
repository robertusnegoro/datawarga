import logging
from typing import Optional
from django.core.files.uploadedfile import UploadedFile
from kependudukan.models import Kompleks, TransaksiIuranBulanan
from kependudukan.errors import (
    ValidationError,
    NotFoundError,
    PaymentAlreadyExistsError,
)

logger = logging.getLogger(__name__)


def record_iuran_payment(
    blok_no: str,
    periode_bulan: str,
    periode_tahun: str,
    total_bayar: str,
    bukti_bayar: Optional[UploadedFile],
) -> TransaksiIuranBulanan:
    """
    Records an Iuran Bulanan payment.
    Validates the format, looks up the kompleks, and checks for existing payments.
    """
    if not blok_no or "/" not in blok_no:
        raise ValidationError("Format alamat tidak valid")

    split_keyword = blok_no.split("/")
    blok = split_keyword[0].strip()
    nomor = split_keyword[1].strip()

    kompleks = Kompleks.objects.filter(blok__icontains=blok, nomor=nomor).first()
    if not kompleks:
        raise NotFoundError("Kompleks", f"{blok}/{nomor}")

    # Check if payment already exists
    existing_payment = TransaksiIuranBulanan.objects.filter(
        kompleks=kompleks,
        periode_bulan=periode_bulan,
        periode_tahun=periode_tahun,
    ).exists()

    if existing_payment:
        raise PaymentAlreadyExistsError(periode_bulan, periode_tahun)

    # Record payment
    try:
        payment = TransaksiIuranBulanan.objects.create(
            kompleks=kompleks,
            periode_bulan=periode_bulan,
            periode_tahun=periode_tahun,
            total_bayar=total_bayar,
            bukti_bayar=bukti_bayar,
        )
        logger.info(f"Recorded payment {payment.id} for kompleks {kompleks.id}")
        return payment
    except Exception as e:
        logger.error(f"Failed to record payment for {blok_no}: {str(e)}", exc_info=True)
        raise ValidationError("Gagal mencatat pembayaran")
