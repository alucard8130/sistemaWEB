from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('facturacion', '0059_llenar_referencia_grupos'),
    ]

    operations = [
        migrations.AddField(
            model_name='grupofacturacion',
            name='referencia_corta',
            field=models.CharField(blank=True, max_length=7, null=True, unique=True),
        ),
    ]
