# Generated by Django 5.2.1 on 2025-06-05 08:54

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('locales', '0009_localcomercial_propietario_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='localcomercial',
            name='propietario',
            field=models.CharField(max_length=255),
        ),
    ]
