# Generated by Django 4.1.4 on 2023-04-06 09:30

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("kependudukan", "0021_alter_transaksiiuranbulanan_periode_bulan_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="summarytransaksibulanan",
            name="april",
            field=models.BooleanField(null=True),
        ),
        migrations.AlterField(
            model_name="summarytransaksibulanan",
            name="august",
            field=models.BooleanField(null=True),
        ),
        migrations.AlterField(
            model_name="summarytransaksibulanan",
            name="december",
            field=models.BooleanField(null=True),
        ),
        migrations.AlterField(
            model_name="summarytransaksibulanan",
            name="february",
            field=models.BooleanField(null=True),
        ),
        migrations.AlterField(
            model_name="summarytransaksibulanan",
            name="january",
            field=models.BooleanField(null=True),
        ),
        migrations.AlterField(
            model_name="summarytransaksibulanan",
            name="july",
            field=models.BooleanField(null=True),
        ),
        migrations.AlterField(
            model_name="summarytransaksibulanan",
            name="june",
            field=models.BooleanField(null=True),
        ),
        migrations.AlterField(
            model_name="summarytransaksibulanan",
            name="march",
            field=models.BooleanField(null=True),
        ),
        migrations.AlterField(
            model_name="summarytransaksibulanan",
            name="may",
            field=models.BooleanField(null=True),
        ),
        migrations.AlterField(
            model_name="summarytransaksibulanan",
            name="november",
            field=models.BooleanField(null=True),
        ),
        migrations.AlterField(
            model_name="summarytransaksibulanan",
            name="october",
            field=models.BooleanField(null=True),
        ),
        migrations.AlterField(
            model_name="summarytransaksibulanan",
            name="september",
            field=models.BooleanField(null=True),
        ),
    ]
