# Generated by Django 4.1.4 on 2023-02-20 01:58

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("kependudukan", "0015_alter_warga_no_hp_transaksiiuranbulanan"),
    ]

    operations = [
        migrations.AlterField(
            model_name="transaksiiuranbulanan",
            name="bukti_bayar",
            field=models.FileField(blank=True, upload_to="bukti_bayar"),
        ),
        migrations.AddIndex(
            model_name="transaksiiuranbulanan",
            index=models.Index(
                fields=["periode_bulan"], name="kependuduka_periode_d75dca_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="transaksiiuranbulanan",
            index=models.Index(
                fields=["periode_tahun"], name="kependuduka_periode_b69792_idx"
            ),
        ),
    ]
