# Generated by Django 4.1.4 on 2023-05-29 02:15

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("kependudukan", "0023_alter_summarytransaksibulanan_april_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="warga",
            name="kepala_keluarga",
            field=models.BooleanField(default=False),
        ),
    ]
