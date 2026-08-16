# ============================================================
# Colócalo en: cualquier_app/management/commands/reset_secuencias.py
# (crea las carpetas management/ y management/commands/ si no
# existen, cada una con su __init__.py vacío)
#
# Uso:
#   python manage.py reset_secuencias
# ============================================================

from django.apps import apps
from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = "Resincroniza todas las secuencias de PostgreSQL con el MAX(id) real de cada tabla."

    def handle(self, *args, **options):
        total_corregidas = 0

        with connection.cursor() as cursor:
            for model in apps.get_models():
                table = model._meta.db_table
                pk_column = model._meta.pk.column

                cursor.execute(
                    "SELECT pg_get_serial_sequence(%s, %s)", [f'"{table}"', pk_column]
                )
                secuencia = cursor.fetchone()[0]
                if not secuencia:
                    continue

                cursor.execute(
                    f'SELECT setval(%s, COALESCE((SELECT MAX("{pk_column}") FROM "{table}"), 1))',
                    [secuencia],
                )
                total_corregidas += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"✅ {total_corregidas} secuencia(s) sincronizada(s) con su tabla correspondiente."
            )
        )