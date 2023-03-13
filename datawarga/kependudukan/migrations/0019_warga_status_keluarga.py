# Generated by Django 4.1.4 on 2023-03-13 07:32

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("kependudukan", "0018_kompleks_kependuduka_blok_2c7004_idx_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="warga",
            name="status_keluarga",
            field=models.CharField(
                choices=[
                    ("SUAMI", "SUAMI"),
                    ("ISTRI", "ISTRI"),
                    ("ANAK", "ANAK"),
                    ("ORANG TUA", "ORANG TUA"),
                    ("SAUDARA", "SAUDARA"),
                    ("LAINNYA", "LAINNYA"),
                    ("N/A", "N/A"),
                ],
                default="N/A",
                max_length=30,
            ),
        ),
    ]
