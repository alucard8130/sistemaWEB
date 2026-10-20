from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('areas', '0027_areacomun_periodicidad_facturacion'),
    ]

    operations = [
        migrations.AddField(
            model_name='areacomun',
            name='referencia_corta',
            field=models.CharField(blank=True, max_length=7, null=True, unique=True),
        ),
    ]
