from django.db import models
from django.conf import settings

# Create your models here.
class Warga(models.Model):
    RELIGIONS = (
        ("islam", "ISLAM"),
        ("kristen katholik", "KATHOLIK"),
        ("kristen protestan", "KRISTEN"),
        ("hindu", "HINDU"),
        ("buddha", "BUDDHA"),
        ("konghucu", "KONGHUCU"),
    )
    JENIS_KELAMIN = (("Laki-laki", "laki-laki"), ("Perempuan", "perempuan"))
    agama = models.CharField(max_length=50, choices=RELIGIONS, default="")
    alamat = models.TextField()
    email = models.EmailField(max_length=200, null=True, blank=True)
    foto_path = models.ImageField(upload_to="uploads/", blank=True)
    kecamatan = models.CharField(max_length=150, default=settings.KECAMATAN)
    kelurahan = models.CharField(max_length=150, default=settings.KELURAHAN)
    kode_pos = models.CharField(max_length=8, null=True, blank=True)
    kota = models.CharField(max_length=150, default=settings.KOTA)
    nama_lengkap = models.CharField(max_length=254)
    nik = models.CharField(max_length=64, unique=True)
    no_hp = models.CharField(max_length=15)
    no_kk = models.CharField(max_length=64, null=True, blank=True)
    provinsi = models.CharField(max_length=150, default=settings.PROVINSI)
    pekerjaan = models.CharField(max_length=128, null=True)
    rt = models.CharField(max_length=4)
    rw = models.CharField(max_length=4)
    status = models.CharField(max_length=50, null=True)
    tanggal_lahir = models.DateField(null=True)
    tempat_lahir = models.CharField(max_length=100, null=True, blank=True)
    jenis_kelamin = models.CharField(
        max_length=30, choices=JENIS_KELAMIN, default="Perempuan"
    )
    kewarganegaraan = models.CharField(
        max_length=250, null=True, blank=True, default="Indonesia/WNI"
    )

    def __str__(self):
        return self.nama_lengkap
