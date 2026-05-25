from datetime import date
from datetime import datetime
from django.conf import settings
from django.contrib.auth.models import User
from django.db import models
import os
import uuid
from django.utils import timezone
from .utils.formatters import format_rupiah


# Create your models here.
class Warga(models.Model):
    RELIGIONS = (
        ("ISLAM", "ISLAM"),
        ("KATHOLIK", "KATHOLIK"),
        ("KRISTEN", "KRISTEN"),
        ("HINDU", "HINDU"),
        ("BUDDHA", "BUDDHA"),
        ("KONGHUCU", "KONGHUCU"),
    )
    STATUS_KAWIN = (
        ("BELUM KAWIN", "BELUM KAWIN"),
        ("KAWIN", "KAWIN"),
        ("CERAI HIDUP", "CERAI HIDUP"),
        ("CERAI MATI", "CERAI MATI"),
    )
    STATUS_TINGGAL = (
        ("KONTRAK", "KONTRAK"),
        ("KOST", "KOST"),
        ("TETAP", "TETAP"),
        ("PINDAH", "PINDAH"),
        ("MENINGGAL", "MENINGGAL"),
        ("LAINNYA", "LAINNYA"),
    )
    PEKERJAAN = (
        ("PELAJAR/MAHASISWA", "PELAJAR/MAHASISWA"),
        ("PNS", "PNS"),
        ("KARYAWAN SWASTA", "KARYAWAN SWASTA"),
        ("KARYAWAN BUMN", "KARYAWAN BUMN"),
        ("TNI", "TNI"),
        ("POLRI", "POLRI"),
        ("NAKES", "NAKES"),
        ("WIRASWASTA", "WIRASWASTA"),
        ("MENGURUS RUMAH TANGGA", "MENGURUS RUMAH TANGGA"),
        ("GURU", "GURU"),
        ("OJEK", "OJEK"),
        ("LAINNYA", "LAINNYA"),
    )

    STATUS_KELUARGA = (
        ("SUAMI", "SUAMI"),
        ("ISTRI", "ISTRI"),
        ("ANAK", "ANAK"),
        ("ORANG TUA", "ORANG TUA"),
        ("SAUDARA", "SAUDARA"),
        ("LAINNYA", "LAINNYA"),
        ("N/A", "N/A"),
    )

    JENIS_KELAMIN = (("LAKI-LAKI", "LAKI-LAKI"), ("PEREMPUAN", "PEREMPUAN"))
    agama = models.CharField(max_length=50, choices=RELIGIONS, default="")

    email = models.EmailField(max_length=200, null=True, blank=True)
    foto_path = models.ImageField(upload_to="uploads/", blank=True)

    nama_lengkap = models.CharField(max_length=254)
    nik = models.CharField(max_length=64, unique=True)
    no_hp = models.CharField(max_length=15, null=True, blank=True)
    no_kk = models.CharField(max_length=64, null=True, blank=True)

    pekerjaan = models.CharField(
        max_length=128, choices=PEKERJAAN, default="KARYAWAN SWASTA"
    )
    status = models.CharField(
        max_length=50, choices=STATUS_KAWIN, default="BELUM KAWIN"
    )
    tanggal_lahir = models.DateField(null=True)
    tempat_lahir = models.CharField(max_length=100, null=True, blank=True)
    jenis_kelamin = models.CharField(
        max_length=30, choices=JENIS_KELAMIN, default="Perempuan"
    )
    kewarganegaraan = models.CharField(
        max_length=250, null=True, blank=True, default="Indonesia/WNI"
    )
    status_tinggal = models.CharField(
        max_length=30, choices=STATUS_TINGGAL, default="TETAP"
    )
    status_keluarga = models.CharField(
        max_length=30, choices=STATUS_KELUARGA, default="N/A"
    )
    alamat_ktp = models.CharField(max_length=255, null=True, blank=True)
    ktp_image_path = models.ImageField(upload_to="uploads/", blank=True)
    kompleks = models.ForeignKey("Kompleks", on_delete=models.SET_NULL, null=True)
    kepala_keluarga = models.BooleanField(default=False)

    class Meta:
        indexes = [
            models.Index(fields=["nama_lengkap"]),
            models.Index(fields=["nik"]),
            models.Index(fields=["no_kk"]),
            models.Index(fields=["agama"]),
            models.Index(fields=["jenis_kelamin"]),
            models.Index(fields=["status_tinggal"]),
        ]

    def __str__(self):
        return self.nama_lengkap


class Kompleks(models.Model):
    alamat = models.CharField(
        max_length=255, default=settings.ALAMAT, null=True, blank=True
    )
    kecamatan = models.CharField(max_length=150, default=settings.KECAMATAN)
    kelurahan = models.CharField(max_length=150, default=settings.KELURAHAN)
    kode_pos = models.CharField(max_length=8, null=True, blank=True)
    kota = models.CharField(max_length=150, default=settings.KOTA)
    provinsi = models.CharField(max_length=150, default=settings.PROVINSI)
    cluster = models.CharField(max_length=50, blank=True, null=True)
    blok = models.CharField(max_length=10, blank=True, null=True)
    nomor = models.CharField(max_length=10, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    rt = models.CharField(max_length=4, default=settings.RUKUNTANGGA)
    rw = models.CharField(max_length=4, default=settings.RUKUNWARGA)
    permission_group = models.ForeignKey(
        "WargaPermissionGroup", on_delete=models.SET_NULL, null=True
    )

    class Meta:
        indexes = [
            models.Index(fields=["blok"]),
            models.Index(fields=["nomor"]),
            models.Index(fields=["cluster"]),
        ]

    def __str__(self):
        return "%s / %s" % (self.blok, self.nomor)


def upload_to(instance, filename):
    """
    Renames the uploaded file to year-month-date.ext
    """
    ext = os.path.splitext(filename)[1]
    today = date.today()
    return "bukti_bayar/{}/{}{}".format(
        today.strftime("%Y-%m-%d"), today.strftime("%Y-%m-%d"), ext
    )


class TransaksiIuranBulanan(models.Model):
    indonesian_months = (
        "Januari",
        "Februari",
        "Maret",
        "April",
        "Mei",
        "Juni",
        "Juli",
        "Agustus",
        "September",
        "Oktober",
        "November",
        "Desember",
    )

    list_bulan_ori = []
    counter = 1
    for a in indonesian_months:
        list_bulan_ori.append((int(counter), a))
        counter += 1

    LIST_BULAN = tuple(list_bulan_ori)

    tanggal_bayar = models.DateField(auto_now_add=True)
    last_modified = models.DateTimeField(auto_now=True)
    kompleks = models.ForeignKey("Kompleks", on_delete=models.SET_NULL, null=True)
    keterangan = models.TextField(blank=True, null=True)
    bukti_bayar = models.FileField(upload_to=upload_to, blank=True)
    periode_bulan = models.IntegerField(choices=LIST_BULAN)
    periode_tahun = models.IntegerField()
    total_bayar = models.IntegerField(default=settings.IURAN_BULANAN)

    class Meta:
        indexes = [
            models.Index(fields=["periode_bulan"]),
            models.Index(fields=["periode_tahun"]),
        ]


class SummaryTransaksiBulanan(models.Model):
    kompleks = models.ForeignKey("Kompleks", on_delete=models.SET_NULL, null=True)
    periode_tahun = models.IntegerField()
    january = models.BooleanField(null=True, default=False)
    february = models.BooleanField(null=True, default=False)
    march = models.BooleanField(null=True, default=False)
    april = models.BooleanField(null=True, default=False)
    may = models.BooleanField(null=True, default=False)
    june = models.BooleanField(null=True, default=False)
    july = models.BooleanField(null=True, default=False)
    august = models.BooleanField(null=True, default=False)
    september = models.BooleanField(null=True, default=False)
    october = models.BooleanField(null=True, default=False)
    november = models.BooleanField(null=True, default=False)
    december = models.BooleanField(null=True, default=False)
    last_modified = models.DateTimeField(auto_now=True)

    def update_month_field(self, month_num, value):
        month_name = datetime.strptime(str(month_num), "%m").strftime("%B").lower()
        field_name = {
            "january": "january",
            "february": "february",
            "march": "march",
            "april": "april",
            "may": "may",
            "june": "june",
            "july": "july",
            "august": "august",
            "september": "september",
            "october": "october",
            "november": "november",
            "december": "december",
        }[month_name]
        setattr(self, field_name, value)
        self.save()


class WargaPermissionGroup(models.Model):
    group_name = models.CharField(max_length=64, unique=True)

    def __str__(self):
        return self.group_name


class UserPermission(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    permission_group = models.ForeignKey(
        "WargaPermissionGroup", on_delete=models.SET_NULL, null=True
    )


class Penandatangan(models.Model):
    nama = models.CharField(max_length=150)
    jabatan = models.CharField(max_length=100)
    aktif = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.nama} ({self.jabatan})"


class Surat(models.Model):
    JENIS_SURAT = (
        ("PENGANTAR_RT", "Surat Pengantar RT"),
        ("KETERANGAN_DOMISILI", "Surat Keterangan Domisili"),
        ("KETERANGAN_TIDAK_MAMPU", "Surat Keterangan Tidak Mampu"),
    )
    warga = models.ForeignKey(Warga, on_delete=models.CASCADE)
    jenis_surat = models.CharField(max_length=50, choices=JENIS_SURAT)
    nomor_surat = models.CharField(max_length=100, blank=True, null=True)
    keperluan = models.TextField()
    tanggal_surat = models.DateField(auto_now_add=True)
    penandatangan = models.ForeignKey(
        Penandatangan, on_delete=models.SET_NULL, null=True
    )

    def __str__(self):
        return f"{self.jenis_surat} - {self.warga.nama_lengkap}"

    @property
    def tanggal_surat_indo(self):
        if not self.tanggal_surat:
            return "-"
        indonesian_months = (
            "Januari",
            "Februari",
            "Maret",
            "April",
            "Mei",
            "Juni",
            "Juli",
            "Agustus",
            "September",
            "Oktober",
            "November",
            "Desember",
        )
        return f"{self.tanggal_surat.day} {indonesian_months[self.tanggal_surat.month - 1]} {self.tanggal_surat.year}"


class Kendaraan(models.Model):
    JENIS_KENDARAAN = (
        ("MOBIL", "MOBIL"),
        ("MOTOR", "MOTOR"),
        ("LAINNYA", "LAINNYA"),
    )
    jenis_kendaraan = models.CharField(
        max_length=50, choices=JENIS_KENDARAAN, default="MOBIL"
    )
    merk = models.CharField(max_length=100, blank=True, null=True)
    tipe = models.CharField(max_length=100, blank=True, null=True)
    plat_nomor = models.CharField(max_length=20, unique=True)
    pemilik = models.ForeignKey("Warga", on_delete=models.CASCADE)
    keterangan = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.plat_nomor} - {self.merk} {self.tipe}"


def upload_kas_to(instance, filename):
    """
    Renames the uploaded file to year-month-date.ext for KasTransaksi
    """
    ext = os.path.splitext(filename)[1]
    today = date.today()
    return "bukti_kas/{}/{}{}".format(
        today.strftime("%Y-%m-%d"), today.strftime("%Y-%m-%d"), ext
    )


class KasTagihan(models.Model):
    JENIS_CHOICES = (
        ("PIUTANG", "Piutang (Receivable)"),
        ("HUTANG", "Hutang (Payable)"),
    )

    KATEGORI_CHOICES = (
        ("IURAN", "Iuran Bulanan"),
        ("SOSIAL", "Sosial/Sumbangan"),
        ("KEBERSIHAN", "Kebersihan"),
        ("KEAMANAN", "Keamanan"),
        ("OPERASIONAL", "Operasional"),
        ("PEMBANGUNAN", "Pembangunan/Infrastruktur"),
        ("LAINNYA", "Lain-lain"),
    )

    STATUS_CHOICES = (
        ("BELUM", "Belum Bayar"),
        ("LUNAS", "Lunas"),
    )

    judul = models.CharField(max_length=200)
    jenis = models.CharField(max_length=20, choices=JENIS_CHOICES)
    kategori = models.CharField(
        max_length=30, choices=KATEGORI_CHOICES, default="LAINNYA"
    )
    jumlah = models.IntegerField()
    tanggal_jatuh_tempo = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="BELUM")
    keterangan = models.TextField(blank=True, null=True)
    tanggal_dibuat = models.DateField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["tanggal_jatuh_tempo"]),
            models.Index(fields=["jenis"]),
            models.Index(fields=["kategori"]),
            models.Index(fields=["status"]),
        ]

    def __str__(self):
        return f"[{self.jenis} - {self.status}] {self.judul} - {format_rupiah(self.jumlah)}"


class KasTransaksi(models.Model):
    JENIS_CHOICES = (
        ("PEMASUKAN", "Pemasukan"),
        ("PENGELUARAN", "Pengeluaran"),
    )

    KATEGORI_CHOICES = (
        ("IURAN", "Iuran Bulanan"),
        ("SOSIAL", "Sosial/Sumbangan"),
        ("KEBERSIHAN", "Kebersihan"),
        ("KEAMANAN", "Keamanan"),
        ("OPERASIONAL", "Operasional"),
        ("PEMBANGUNAN", "Pembangunan/Infrastruktur"),
        ("LAINNYA", "Lain-lain"),
    )

    tanggal = models.DateField(default=date.today)
    jenis = models.CharField(max_length=20, choices=JENIS_CHOICES)
    kategori = models.CharField(
        max_length=30, choices=KATEGORI_CHOICES, default="LAINNYA"
    )
    jumlah = models.IntegerField()
    keterangan = models.TextField(blank=True, null=True)
    bukti_transaksi = models.FileField(upload_to=upload_kas_to, blank=True, null=True)
    iuran_asal = models.ForeignKey(
        "TransaksiIuranBulanan",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="kas_transaksi",
    )
    tagihan_asal = models.ForeignKey(
        "KasTagihan",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="pembayaran",
    )

    class Meta:
        indexes = [
            models.Index(fields=["tanggal"]),
            models.Index(fields=["jenis"]),
            models.Index(fields=["kategori"]),
        ]

    def __str__(self):
        return f"[{self.jenis}] {self.tanggal} - {format_rupiah(self.jumlah)} ({self.kategori})"


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    foto = models.ImageField(upload_to="profile_pics/", blank=True, null=True)
    failed_login_attempts = models.IntegerField(default=0)
    shadow_ban_expires_at = models.DateTimeField(null=True, blank=True)
    is_permanently_locked = models.BooleanField(default=False)
    mfa_enabled = models.BooleanField(default=False)
    totp_secret = models.CharField(max_length=32, null=True, blank=True)

    def __str__(self) -> str:
        return f"Profile for {self.user.username}"


class UserInvitation(models.Model):
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="invitation"
    )
    token = models.CharField(max_length=64, unique=True, default=uuid.uuid4)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)

    def is_expired(self) -> bool:
        return timezone.now() > self.expires_at

    def is_valid(self) -> bool:
        return not self.is_used and not self.is_expired()

    def __str__(self) -> str:
        return f"Invitation for {self.user.username} (Valid: {self.is_valid()})"
