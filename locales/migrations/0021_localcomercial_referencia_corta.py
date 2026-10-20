from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('locales', '0020_localcomercial_pool_vacancia'),
    ]

    operations = [
        migrations.AddField(
            model_name='localcomercial',
            name='referencia_corta',
            field=models.CharField(blank=True, max_length=7, null=True, unique=True),
        ),
    ]
