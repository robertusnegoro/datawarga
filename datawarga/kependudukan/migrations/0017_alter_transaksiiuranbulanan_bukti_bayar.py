# Generated by Django 4.1.4 on 2023-03-03 02:58

from django.db import migrations, models
import kependudukan.models


class Migration(migrations.Migration):

    dependencies = [
        ("kependudukan", "0016_transaksiiuranbulanan_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="transaksiiuranbulanan",
            name="bukti_bayar",
            field=models.FileField(blank=True, upload_to=kependudukan.models.upload_to),
        ),
    ]
