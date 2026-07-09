# Generated manually (dividida en 3 pasos para evitar el bug de
# default=uuid.uuid4 + unique=True sobre filas existentes)

import django.db.models.deletion
import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('empleados', '0005_incidencia_importe'),
    ]

    operations = [
        migrations.AddField(
            model_name='empleado',
            name='hora_entrada_esperada',
            field=models.TimeField(blank=True, help_text='Hora esperada de entrada, ej. 08:00', null=True),
        ),
        migrations.AddField(
            model_name='empleado',
            name='hora_salida_esperada',
            field=models.TimeField(blank=True, help_text='Hora esperada de salida, ej. 17:00', null=True),
        ),
        migrations.AddField(
            model_name='empleado',
            name='tolerancia_minutos',
            field=models.PositiveIntegerField(default=10, help_text='Minutos de gracia antes de contar retardo'),
        ),
        # OJO: aqui todavia SIN unique=True. Se agrega hasta el paso 3,
        # despues de rellenar valores unicos para las filas existentes.
        migrations.AddField(
            model_name='empleado',
            name='token_asistencia',
            field=models.UUIDField(default=uuid.uuid4, editable=False, help_text='Identifica al empleado en el link de marcar asistencia (sin necesidad de login).', null=True),
        ),
        migrations.CreateModel(
            name='RegistroAsistencia',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('fecha', models.DateField()),
                ('hora_entrada', models.DateTimeField(blank=True, null=True)),
                ('lat_entrada', models.DecimalField(blank=True, decimal_places=7, max_digits=10, null=True)),
                ('lng_entrada', models.DecimalField(blank=True, decimal_places=7, max_digits=10, null=True)),
                ('distancia_metros_entrada', models.FloatField(blank=True, null=True)),
                ('dentro_de_rango_entrada', models.BooleanField(blank=True, null=True)),
                ('hora_salida', models.DateTimeField(blank=True, null=True)),
                ('lat_salida', models.DecimalField(blank=True, decimal_places=7, max_digits=10, null=True)),
                ('lng_salida', models.DecimalField(blank=True, decimal_places=7, max_digits=10, null=True)),
                ('distancia_metros_salida', models.FloatField(blank=True, null=True)),
                ('dentro_de_rango_salida', models.BooleanField(blank=True, null=True)),
                ('empleado', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='registros_asistencia', to='empleados.empleado')),
            ],
            options={
                'verbose_name': 'Registro de Asistencia',
                'verbose_name_plural': 'Registros de Asistencia',
                'ordering': ['-fecha'],
                'unique_together': {('empleado', 'fecha')},
            },
        ),
    ]
