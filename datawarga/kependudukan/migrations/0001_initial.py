# Generated by Django 4.1.4 on 2022-12-10 11:07

from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Warga",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "agama",
                    models.CharField(
                        choices=[
                            ("Islam", "islam"),
                            ("Kristen Katholik", "katholik"),
                            ("Kristen Protestan", "kristen"),
                            ("Hindu", "hindu"),
                            ("Buddha", "buddha"),
                            ("Konghucu", "konghucu"),
                        ],
                        default="",
                        max_length=50,
                    ),
                ),
                ("alamat", models.TextField()),
                ("email", models.EmailField(blank=True, max_length=200, null=True)),
                ("foto_path", models.ImageField(blank=True, upload_to="uploads/")),
                ("kecamatan", models.CharField(default="SETU", max_length=150)),
                ("kelurahan", models.CharField(default="BABAKAN", max_length=150)),
                ("kode_pos", models.CharField(blank=True, max_length=8, null=True)),
                ("kota", models.CharField(default="TANGERANG SELATAN", max_length=150)),
                ("nama_lengkap", models.CharField(max_length=254)),
                ("nik", models.CharField(max_length=64)),
                ("no_hp", models.CharField(max_length=15)),
                ("no_kk", models.CharField(blank=True, max_length=64, null=True)),
                ("provinsi", models.CharField(default="BANTEN", max_length=150)),
                ("pekerjaan", models.CharField(max_length=128, null=True)),
                ("rt", models.CharField(max_length=4)),
                ("rw", models.CharField(max_length=4)),
                ("status", models.CharField(max_length=50, null=True)),
                ("tanggal_lahir", models.DateField(null=True)),
                (
                    "tempat_lahir",
                    models.CharField(blank=True, max_length=100, null=True),
                ),
                (
                    "jenis_kelamin",
                    models.CharField(
                        choices=[
                            ("Islam", "islam"),
                            ("Kristen Katholik", "katholik"),
                            ("Kristen Protestan", "kristen"),
                            ("Hindu", "hindu"),
                            ("Buddha", "buddha"),
                            ("Konghucu", "konghucu"),
                        ],
                        default="Perempuan",
                        max_length=30,
                    ),
                ),
                (
                    "kewarganegaraan",
                    models.CharField(
                        blank=True, default="Indonesia/WNI", max_length=250, null=True
                    ),
                ),
            ],
        ),
    ]
