# Generated by Django 4.1.4 on 2023-01-16 06:52

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("kependudukan", "0009_kompleks_rt_kompleks_rw"),
    ]

    operations = [
        migrations.AlterField(
            model_name="warga",
            name="alamat",
            field=models.CharField(
                blank=True, default="Jalan Nirwana", max_length=255, null=True
            ),
        ),
    ]
