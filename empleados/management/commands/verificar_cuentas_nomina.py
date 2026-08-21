# ============================================================
# Colócalo en: empleados/management/commands/verificar_cuentas_nomina.py
# (crea las carpetas management/ y management/commands/ si no
# existen, cada una con su __init__.py vacío)
#
# Uso:
#   python manage.py verificar_cuentas_nomina
#   python manage.py verificar_cuentas_nomina --empresa 3
#
# NO modifica nada -- solo diagnostica. Corre esto ANTES de la
# primera dispersión real en producción, para cada empresa que ya
# tenga cuentas de sueldo creadas manualmente.
# ============================================================

import difflib

from django.core.management.base import BaseCommand

from empleados.models import Empleado  # ajusta el import a tu ruta real
from gastos.models import TipoGasto  # ajusta el import a tu ruta real


class Command(BaseCommand):
    help = "Verifica que cada empleado activo tenga (o no) una cuenta 'Sueldo {nombre}' ya creada, y sugiere posibles coincidencias si el nombre no calza exacto."

    def add_arguments(self, parser):
        parser.add_argument("--empresa", type=int, default=None, help="ID de una empresa especifica (opcional).")

    def handle(self, *args, **options):
        empresa_id = options.get("empresa")

        empleados_qs = Empleado.objects.filter(activo=True).select_related("empresa")
        if empresa_id:
            empleados_qs = empleados_qs.filter(empresa_id=empresa_id)

        empleados_qs = empleados_qs.order_by("empresa_id", "nombre")

        total_ok = 0
        total_nuevos = 0
        total_sospechosos = 0

        empresa_actual = None

        for empleado in empleados_qs:
            if empleado.empresa_id != empresa_actual:
                empresa_actual = empleado.empresa_id
                self.stdout.write("")
                self.stdout.write(self.style.HTTP_INFO(f"=== {empleado.empresa.nombre} ==="))

            nombre_esperado = f"Sueldo {empleado.nombre}"

            cuentas_existentes = list(
                TipoGasto.objects.filter(
                    empresa=empleado.empresa,
                    subgrupo__grupo__nombre="Gastos Nomina",
                    subgrupo__nombre="Sueldos y salarios",
                ).values_list("nombre", flat=True)
            )

            if nombre_esperado in cuentas_existentes:
                total_ok += 1
                continue

            parecidos_nombres = difflib.get_close_matches(
                empleado.nombre,
                [c.replace("Sueldo ", "", 1) for c in cuentas_existentes],
                n=3, cutoff=0.75,
            )
            parecidos = [f"Sueldo {n}" for n in parecidos_nombres]

            if parecidos:
                total_sospechosos += 1
                self.stdout.write(self.style.WARNING(
                    f"  AVISO: {empleado.nombre} -- se esperaba \"{nombre_esperado}\", "
                    f"pero no existe exacto. Posibles coincidencias: {parecidos}"
                ))
            else:
                total_nuevos += 1
                self.stdout.write(
                    f"  - {empleado.nombre} -- sin cuenta previa (se creara nueva, \"{nombre_esperado}\") -- normal si nunca ha cobrado."
                )

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS(f"{total_ok} empleado(s) con cuenta ya coincidente exacta."))
        self.stdout.write(f"{total_nuevos} empleado(s) sin cuenta previa (se crearan nuevas, sin conflicto).")
        if total_sospechosos:
            self.stdout.write(self.style.ERROR(
                f"{total_sospechosos} empleado(s) con posible desfase de nombre -- revisalos ANTES de dispersar, "
                f"corrigiendo el nombre del Empleado o el de la cuenta para que coincidan exacto."
            ))
        else:
            self.stdout.write(self.style.SUCCESS("0 casos sospechosos -- ningun nombre casi-coincidente detectado."))