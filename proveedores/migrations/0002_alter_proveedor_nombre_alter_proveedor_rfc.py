# Generated by Django 5.2.1 on 2025-07-25 22:54

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('proveedores', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='proveedor',
            name='nombre',
            field=models.CharField(max_length=100),
        ),
        migrations.AlterField(
            model_name='proveedor',
            name='rfc',
            field=models.CharField(default='', max_length=13, unique=True),
        ),
    ]
