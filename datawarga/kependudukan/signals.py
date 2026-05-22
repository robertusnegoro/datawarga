from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from kependudukan.models import TransaksiIuranBulanan, KasTransaksi


@receiver(post_save, sender=TransaksiIuranBulanan)
def sync_iuran_to_kas_post_save(sender, instance, created, **kwargs):
    """
    Automatically creates or updates a KasTransaksi record when a
    TransaksiIuranBulanan is saved.
    """
    # Build a standard keterangan for auto-sync
    keterangan_auto = (
        instance.keterangan
        or f"Iuran Bulanan RT/RW - Kompleks {instance.kompleks} (Bulan {instance.periode_bulan}, Tahun {instance.periode_tahun})"
    )

    # Update or create the KasTransaksi entry
    kas_entry, _ = KasTransaksi.objects.update_or_create(
        iuran_asal=instance,
        defaults={
            "tanggal": instance.tanggal_bayar,
            "jenis": "PEMASUKAN",
            "kategori": "IURAN",
            "jumlah": instance.total_bayar,
            "keterangan": keterangan_auto,
            "bukti_transaksi": instance.bukti_bayar if instance.bukti_bayar else None,
        },
    )


@receiver(post_delete, sender=TransaksiIuranBulanan)
def sync_iuran_to_kas_post_delete(sender, instance, **kwargs):
    """
    Automatically deletes the corresponding KasTransaksi record when a
    TransaksiIuranBulanan is deleted.
    """
    KasTransaksi.objects.filter(iuran_asal=instance).delete()
