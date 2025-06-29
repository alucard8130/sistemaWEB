# Generated by Django 5.2.1 on 2025-06-20 03:32

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('empresas', '0001_initial'),
        ('gastos', '0013_alter_subgrupogasto_options_grupogasto_empresa_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='grupogasto',
            name='empresa',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='empresas.empresa'),
        ),
        migrations.AlterField(
            model_name='subgrupogasto',
            name='empresa',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='empresas.empresa'),
        ),
        migrations.AlterField(
            model_name='tipogasto',
            name='empresa',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='empresas.empresa'),
        ),
    ]
