from django.db import migrations

def cargar_grupos_subgrupos(apps, schema_editor):
    GrupoGasto = apps.get_model('gastos', 'GrupoGasto')
    SubgrupoGasto = apps.get_model('gastos', 'SubgrupoGasto')

    grupos = {
        'Gastos Administracion': ['Papelería', 'Suministros', 'Honorarios', 'Servicios profesionales', 'Oficina','Asamblea', 'Comite', 'Viajes', 'Software', 'Hardware'],
        'Gastos Extraordinarios': ['Reparaciones mayores', 'Proyectos especiales', 'Imprevistos', 'Legales','Contingencias'],
        'Gastos Financieros': ['Comisiones bancarias', 'Intereses', 'Cobranza', 'Inversión'],
        'Gastos Mantenimientos': [ 'Preventivo','Correctivo', 'Equipos', 'Instalaciones', 'Software', 'Edificio','Infraestructura','Hardware'],
        'Gastos Nomina': ['Sueldos y salarios', 'Prestaciones', 'Seguridad social', 'Impuestos', 'Indemnizaciones','Infonavit','Prestamos'],
        'Gastos Operacion': ['Transporte', 'Logística', 'Alquiler de equipos','Seguros','Proteccion Civil','Insumos','Combustibles'],
        'Gastos Publicidad': ['Digital', 'Impresos', 'Eventos', 'Promociones', 'Marketing','Decoracion'],
        'Gastos Servicios': ['Agua', 'Luz', 'Teléfonia', 'Internet', 'Seguridad','Limpieza','Jardinería'],
    }

    for grupo_nombre, subgrupos in grupos.items():
        grupo, _ = GrupoGasto.objects.get_or_create(nombre=grupo_nombre)
        for subgrupo_nombre in subgrupos:
            SubgrupoGasto.objects.get_or_create(grupo=grupo, nombre=subgrupo_nombre)

class Migration(migrations.Migration):

    dependencies = [
        ('gastos', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(cargar_grupos_subgrupos),
    ]