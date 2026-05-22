import logging
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.contrib.auth.models import User
from kependudukan.models import TransaksiIuranBulanan, KasTransaksi, UserProfile

logger = logging.getLogger(__name__)


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


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """
    Automatically creates a UserProfile when a User is created.
    """
    if created:
        UserProfile.objects.get_or_create(user=instance)


@receiver(post_save, sender=User)
def reset_lockout_on_activation(sender, instance, **kwargs):
    """
    Automatically resets the profile lockout fields if the user is marked active.
    """
    if instance.is_active:
        try:
            profile = instance.profile
            if (
                profile.is_permanently_locked
                or profile.failed_login_attempts > 0
                or profile.shadow_ban_expires_at is not None
            ):
                profile.is_permanently_locked = False
                profile.failed_login_attempts = 0
                profile.shadow_ban_expires_at = None
                profile.save()
                logger.info(
                    "User profile lockout reset on activation",
                    extra={
                        "operation": "reset_lockout_on_activation",
                        "username": instance.username,
                        "userId": instance.id,
                    },
                )
        except UserProfile.DoesNotExist:
            pass
