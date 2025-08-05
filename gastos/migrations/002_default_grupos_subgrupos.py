from django.db import migrations

def cargar_grupos_subgrupos(apps, schema_editor):
    GrupoGasto = apps.get_model('gastos', 'GrupoGasto')
    SubgrupoGasto = apps.get_model('gastos', 'SubgrupoGasto')

    grupos = {
        'Gastos Administracion': ['Papelería', 'Suministros', 'Mobiliario oficina','Asamblea', 'Comite', 'Viajes', 'Software', 'Hardware', 'Equipo de oficina', 'Otros'],

        'Gastos Nomina': ['Sueldos y salarios', 'Prestaciones', 'Seguridad social', 'Impuestos', 'Indemnizaciones','Infonavit','Prestamos','Aguinaldo', 'Vacaciones',
                           'Prima vacacional','Vales de despensa','Uniformes','Despensas', 'Capacitacion', 'Reclutamiento', 'Otros'],
        
        'Gastos Mantenimientos': ['Equipos', 'Instalaciones', 'Software', 'Edificio','Infraestructura','Hardware', 'Vehículos', 'Maquinaria', 'Herramientas','Sistemas de seguridad','Otros'],
        
        'Gastos Servicios': ['Agua', 'Luz', 'Telefonia', 'Internet', 'Seguridad','Limpieza','Jardinería','Recoleccion de basura','Fumigacion','Contables','Legales','Administrativos',
                             'Consultoria','Notariales', 'Auditoría','Otros'],
        
        'Gastos Operacion': ['Transporte', 'Logística','Decoracion', 'Alquiler de equipos','Seguros','Proteccion Civil','Insumos','Combustibles', 'Herramientas','Permisos','Licencias',
                             'Estacionamiento','Sistemas de seguridad','Otros'],
        
        'Gastos Financieros': ['Comisiones', 'Intereses', 'Cobranza', 'Inversión', 'Otros'],
        
        'Gastos Publicidad': ['Digital', 'Impresos', 'Eventos', 'Promociones', 'Marketing','Television','Radio','Patrocinios', 'Otros'],
        
        'Gastos Extraordinarios': ['Reparaciones mayores', 'Proyectos especiales', 'Imprevistos', 'Legales','Contingencias', 'Otros'],
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