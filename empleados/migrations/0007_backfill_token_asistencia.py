import uuid
from django.db import migrations


def asignar_tokens_unicos(apps, schema_editor):
    Empleado = apps.get_model('empleados', 'Empleado')
    for empleado in Empleado.objects.all():
        empleado.token_asistencia = uuid.uuid4()
        empleado.save(update_fields=['token_asistencia'])


def revertir(apps, schema_editor):
    # No hay nada que revertir: los tokens simplemente se quedarian, y el
    # paso 1 al revertirse elimina la columna completa de todos modos.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('empleados', '0006_empleado_asistencia_paso1'),
    ]

    operations = [
        migrations.RunPython(asignar_tokens_unicos, revertir),
    ]
