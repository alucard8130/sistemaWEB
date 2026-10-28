from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('escuelas', '0009_ingresoescuela_clave_unica_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='ingresoescuela',
            name='grado',
            field=models.CharField(blank=True, default='', max_length=30),
        ),
        migrations.AddField(
            model_name='ingresoescuela',
            name='grupo',
            field=models.CharField(blank=True, default='', max_length=30),
        ),
    ]
