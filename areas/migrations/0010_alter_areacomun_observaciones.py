# Generated by Django 5.2.1 on 2025-06-04 18:28

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('areas', '0009_rename_fecha_inicio_areacomun_fecha_inicial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='areacomun',
            name='observaciones',
            field=models.CharField(blank=True, null=True),
        ),
    ]
