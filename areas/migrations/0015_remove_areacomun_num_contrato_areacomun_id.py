# Generated by Django 5.2.1 on 2025-06-09 18:54

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('areas', '0014_areacomun_giro'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='areacomun',
            name='num_contrato',
        ),
        migrations.AddField(
            model_name='areacomun',
            name='id',
            field=models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID'),
        ),
    ]
