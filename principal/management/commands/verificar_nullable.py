# ============================================================
# Colocalo en: cualquier_app/management/commands/verificar_nullable.py
# (crea las carpetas management/ y management/commands/ si no
# existen, cada una con su __init__.py vacio)
#
# Uso:
#   python manage.py verificar_nullable
#   python manage.py verificar_nullable --app proveedores
#
# NO modifica nada -- solo diagnostica, comparando lo que cada
# modelo Django DICE (null=True/False) contra lo que la base de
# datos real PERMITE, columna por columna. Corre esto en produccion
# para detectar el mismo tipo de desfase que encontramos en "rfc".
# ============================================================

from django.apps import apps
from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = (
        "Compara los campos null=True/False de tus modelos Django contra "
        "lo que realmente permite la base de datos -- detecta migraciones "
        "marcadas como aplicadas que nunca corrieron el SQL real."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--app", type=str, default=None,
            help="Limita la revision a una sola app (ej. 'proveedores'). Por default revisa todas."
        )

    def handle(self, *args, **options):
        app_filtro = options.get("app")

        modelos = apps.get_models()
        if app_filtro:
            modelos = [m for m in modelos if m._meta.app_label == app_filtro]

        desfases = []
        total_revisados = 0
        tablas_no_encontradas = []

        with connection.cursor() as cursor:
            for model in modelos:
                table_name = model._meta.db_table

                cursor.execute(
                    """
                    SELECT column_name, is_nullable
                    FROM information_schema.columns
                    WHERE table_schema = 'public' AND table_name = %s
                    """,
                    [table_name],
                )
                columnas_bd = {row[0]: row[1] for row in cursor.fetchall()}

                if not columnas_bd:
                    tablas_no_encontradas.append(table_name)
                    continue

                for field in model._meta.get_fields():
                    if not hasattr(field, "column") or field.column is None:
                        continue
                    if getattr(field, "many_to_many", False):
                        continue

                    column_name = field.column
                    if column_name not in columnas_bd:
                        continue

                    total_revisados += 1
                    nullable_bd = columnas_bd[column_name] == "YES"
                    nullable_django = getattr(field, "null", False)

                    if nullable_django != nullable_bd:
                        desfases.append({
                            "modelo": f"{model._meta.app_label}.{model.__name__}",
                            "tabla": table_name,
                            "campo": field.name,
                            "columna": column_name,
                            "django_null": nullable_django,
                            "bd_nullable": nullable_bd,
                        })

        self.stdout.write(f"Revisados {total_revisados} campo(s) en {len(modelos)} modelo(s).\n")

        if tablas_no_encontradas:
            self.stdout.write(self.style.WARNING(
                f"Nota: {len(tablas_no_encontradas)} modelo(s) no tienen tabla en esta base de datos "
                f"(normal para modelos abstractos, vistas, o managed=False) -- se omitieron.\n"
            ))

        if not desfases:
            self.stdout.write(self.style.SUCCESS("No se encontraron desfases -- todo coincide entre Django y la base de datos."))
            return

        self.stdout.write(self.style.ERROR(f"{len(desfases)} desfase(s) encontrado(s):\n"))
        for d in desfases:
            self.stdout.write(
                f"  {d['modelo']} -- campo '{d['campo']}' (columna '{d['columna']}' en tabla '{d['tabla']}')\n"
                f"    Django dice null={d['django_null']}  |  Base de datos real permite NULL: {d['bd_nullable']}\n"
            )

        self.stdout.write(self.style.WARNING(
            "\nPara corregir cada uno, entra a dbshell y corre:\n"
            "  ALTER TABLE <tabla> ALTER COLUMN <columna> DROP NOT NULL;   -- si Django dice null=True\n"
            "  ALTER TABLE <tabla> ALTER COLUMN <columna> SET NOT NULL;    -- si Django dice null=False\n"
            "(el segundo caso es mas delicado -- revisa primero que no haya filas con NULL ya guardado)"
        ))