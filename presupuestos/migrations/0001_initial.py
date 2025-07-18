# Generated by Django 5.2.1 on 2025-07-16 03:22

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('empresas', '0001_initial'),
        ('facturacion', '0033_alter_tipootroingreso_nombre'),
        ('gastos', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Presupuesto',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('anio', models.PositiveIntegerField()),
                ('mes', models.PositiveSmallIntegerField(blank=True, null=True)),
                ('monto', models.DecimalField(decimal_places=2, max_digits=14)),
                ('empresa', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='empresas.empresa')),
                ('grupo', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='gastos.grupogasto')),
                ('subgrupo', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to='gastos.subgrupogasto')),
                ('tipo_gasto', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to='gastos.tipogasto')),
            ],
            options={
                'unique_together': {('empresa', 'grupo', 'subgrupo', 'tipo_gasto', 'anio', 'mes')},
            },
        ),
        migrations.CreateModel(
            name='PresupuestoCierre',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('anio', models.PositiveIntegerField()),
                ('cerrado', models.BooleanField(default=False)),
                ('fecha_cierre', models.DateTimeField(blank=True, null=True)),
                ('cerrado_por', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
                ('empresa', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='empresas.empresa')),
            ],
            options={
                'unique_together': {('empresa', 'anio')},
            },
        ),
        migrations.CreateModel(
            name='PresupuestoIngreso',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('anio', models.PositiveIntegerField()),
                ('mes', models.PositiveIntegerField()),
                ('origen', models.CharField(choices=[('local', 'Locales'), ('area', 'Áreas comunes'), ('otros', 'Otros ingresos')], max_length=10)),
                ('monto_presupuestado', models.DecimalField(decimal_places=2, max_digits=12)),
                ('empresa', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='empresas.empresa')),
                ('tipo_otro', models.ForeignKey(blank=True, help_text="Solo se usa si origen='otros'", null=True, on_delete=django.db.models.deletion.SET_NULL, to='facturacion.tipootroingreso')),
            ],
            options={
                'unique_together': {('empresa', 'anio', 'mes', 'origen', 'tipo_otro')},
            },
        ),
    ]
