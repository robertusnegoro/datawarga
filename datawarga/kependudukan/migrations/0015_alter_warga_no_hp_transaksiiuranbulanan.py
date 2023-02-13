# Generated by Django 4.1.4 on 2023-02-13 10:06

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("kependudukan", "0014_alter_warga_agama_alter_warga_jenis_kelamin"),
    ]

    operations = [
        migrations.AlterField(
            model_name="warga",
            name="no_hp",
            field=models.CharField(blank=True, max_length=15, null=True),
        ),
        migrations.CreateModel(
            name="TransaksiIuranBulanan",
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
                ("tanggal_bayar", models.DateField(auto_now_add=True)),
                ("timestamp_transaksi", models.DateTimeField(auto_now=True)),
                ("keterangan", models.TextField(blank=True, null=True)),
                ("bukti_bayar", models.FileField(upload_to="bukti_bayar")),
                (
                    "periode_bulan",
                    models.CharField(
                        choices=[
                            ("January", "January"),
                            ("February", "February"),
                            ("March", "March"),
                            ("April", "April"),
                            ("May", "May"),
                            ("June", "June"),
                            ("July", "July"),
                            ("August", "August"),
                            ("September", "September"),
                            ("October", "October"),
                            ("November", "November"),
                            ("December", "December"),
                        ],
                        max_length=30,
                    ),
                ),
                ("periode_tahun", models.IntegerField()),
                ("total_bayar", models.IntegerField(default=150000)),
                (
                    "kompleks",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to="kependudukan.kompleks",
                    ),
                ),
            ],
        ),
    ]