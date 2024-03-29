# Generated by Django 4.1.4 on 2022-12-30 07:34

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("kependudukan", "0007_warga_alamat_ktp"),
    ]

    operations = [
        migrations.CreateModel(
            name="Kompleks",
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
                ("cluster", models.CharField(blank=True, max_length=50, null=True)),
                ("blok", models.CharField(blank=True, max_length=10, null=True)),
                ("nomor", models.CharField(blank=True, max_length=10, null=True)),
                ("description", models.TextField(blank=True, null=True)),
            ],
        ),
        migrations.AddField(
            model_name="warga",
            name="kompleks",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to="kependudukan.kompleks",
            ),
        ),
    ]
