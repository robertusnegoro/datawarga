# Generated by Django 4.1.4 on 2023-01-19 01:35

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("kependudukan", "0012_remove_warga_rt_remove_warga_rw"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="warga",
            name="alamat",
        ),
        migrations.RemoveField(
            model_name="warga",
            name="kecamatan",
        ),
        migrations.RemoveField(
            model_name="warga",
            name="kelurahan",
        ),
        migrations.RemoveField(
            model_name="warga",
            name="kode_pos",
        ),
        migrations.RemoveField(
            model_name="warga",
            name="kota",
        ),
        migrations.RemoveField(
            model_name="warga",
            name="provinsi",
        ),
        migrations.AddField(
            model_name="kompleks",
            name="alamat",
            field=models.CharField(
                blank=True, default="Jalan Nirwana", max_length=255, null=True
            ),
        ),
        migrations.AddField(
            model_name="kompleks",
            name="kecamatan",
            field=models.CharField(default="SETU", max_length=150),
        ),
        migrations.AddField(
            model_name="kompleks",
            name="kelurahan",
            field=models.CharField(default="BABAKAN", max_length=150),
        ),
        migrations.AddField(
            model_name="kompleks",
            name="kode_pos",
            field=models.CharField(blank=True, max_length=8, null=True),
        ),
        migrations.AddField(
            model_name="kompleks",
            name="kota",
            field=models.CharField(default="TANGERANG SELATAN", max_length=150),
        ),
        migrations.AddField(
            model_name="kompleks",
            name="provinsi",
            field=models.CharField(default="BANTEN", max_length=150),
        ),
    ]
