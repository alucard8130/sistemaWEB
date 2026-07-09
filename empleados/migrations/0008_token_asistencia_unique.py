import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('empleados', '0007_backfill_token_asistencia'),
    ]

    operations = [
        migrations.AlterField(
            model_name='empleado',
            name='token_asistencia',
            field=models.UUIDField(default=uuid.uuid4, editable=False, help_text='Identifica al empleado en el link de marcar asistencia (sin necesidad de login).', unique=True),
        ),
    ]
