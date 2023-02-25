from django.db import models
from django.conf import settings
import calendar

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
    alamat_ktp = models.CharField(max_length=255, null=True, blank=True)
    kompleks = models.ForeignKey("Kompleks", on_delete=models.SET_NULL, null=True)

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

    def __str__(self):
        return "%s / %s" % (self.blok, self.nomor)


class TransaksiIuranBulanan(models.Model):
    LIST_BULAN = tuple((x, x) for x in list(calendar.month_name))[1:]

    tanggal_bayar = models.DateField(auto_now_add=True)
    last_modified = models.DateTimeField(auto_now=True)
    kompleks = models.ForeignKey("Kompleks", on_delete=models.SET_NULL, null=True)
    keterangan = models.TextField(blank=True, null=True)
    bukti_bayar = models.FileField(upload_to="bukti_bayar", blank=True)
    periode_bulan = models.CharField(max_length=30, choices=LIST_BULAN)
    periode_tahun = models.IntegerField()
    total_bayar = models.IntegerField(default=settings.IURAN_BULANAN)

    class Meta:
        indexes = [
            models.Index(fields=["periode_bulan"]),
            models.Index(fields=["periode_tahun"]),
        ]
