from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('facturacion', '0057_factura_monto_base_factura_monto_iva_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='grupofacturacion',
            name='referencia_pago',
            field=models.CharField(blank=True, max_length=32, null=True, unique=True),
        ),
    ]
