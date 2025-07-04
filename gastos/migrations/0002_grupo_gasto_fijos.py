# Generated by Django 5.2.1 on 2025-06-10 21:02

from django.db import migrations
def crear_grupos_gasto(apps, schema_editor):
    GrupoGasto = apps.get_model('gastos', 'GrupoGasto')
    grupos = [
        "Gastos Nómina",
        "Gastos Administración",
        "Gastos Mantenimiento",
        "Gastos Servicios",
        "Gastos Financieros",
        "Gastos Publicidad",
        "Gastos Extraordinarios",
    ]
    for nombre in grupos:
        GrupoGasto.objects.get_or_create(nombre=nombre)


class Migration(migrations.Migration):

    dependencies = [
        ('gastos', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(crear_grupos_gasto),
    ]
