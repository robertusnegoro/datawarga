# Generated by Django 4.1.4 on 2022-12-16 04:24

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("kependudukan", "0005_warga_alamat_blok_warga_alamat_nomor_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="warga",
            name="alamat",
            field=models.CharField(default="Jalan Nirwana", max_length=255),
        ),
    ]