# Generated by Django 4.1.4 on 2023-01-04 13:22

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("kependudukan", "0008_kompleks_warga_kompleks"),
    ]

    operations = [
        migrations.AddField(
            model_name="kompleks",
            name="rt",
            field=models.CharField(default="006", max_length=4),
        ),
        migrations.AddField(
            model_name="kompleks",
            name="rw",
            field=models.CharField(default="012", max_length=4),
        ),
    ]
