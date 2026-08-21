# ============================================================
# Colocalo en: empleados/management/commands/renombrar_cuentas_nomina.py
#
# Uso:
#   python manage.py renombrar_cuentas_nomina              -> SOLO MUESTRA, no cambia nada
#   python manage.py renombrar_cuentas_nomina --aplicar    -> SI renombra
#   python manage.py renombrar_cuentas_nomina --empresa 3  -> limita a una empresa
#
# Por seguridad, SOLO renombra cuando encuentra EXACTAMENTE UNA cuenta
# candidata para un empleado -- si hay 0 o 2+ posibles coincidencias,
# lo deja intacto y te avisa para que lo revises a mano.
# ============================================================

from django.core.management.base import BaseCommand
from django.db import transaction

from empleados.models import Empleado  # ajusta el import a tu ruta real
from gastos.models import TipoGasto  # ajusta el import a tu ruta real


class Command(BaseCommand):
    help = "Renombra las cuentas 'Sueldo X' existentes para que coincidan con el nombre completo del Empleado correspondiente."

    def add_arguments(self, parser):
        parser.add_argument("--aplicar", action="store_true", help="Aplica los cambios de verdad (sin esto, solo muestra que haria).")
        parser.add_argument("--empresa", type=int, default=None, help="ID de una empresa especifica (opcional).")

    def handle(self, *args, **options):
        aplicar = options.get("aplicar")
        empresa_id = options.get("empresa")

        empleados_qs = Empleado.objects.filter(activo=True).select_related("empresa")
        if empresa_id:
            empleados_qs = empleados_qs.filter(empresa_id=empresa_id)
        empleados_qs = empleados_qs.order_by("empresa_id", "nombre")

        modo = "APLICANDO CAMBIOS" if aplicar else "MODO PRUEBA (nada se guarda todavia)"
        self.stdout.write(self.style.HTTP_INFO(f"=== {modo} ==="))

        renombrados = 0
        ambiguos = 0
        sin_cambio = 0
        empresa_actual = None

        for empleado in empleados_qs:
            if empleado.empresa_id != empresa_actual:
                empresa_actual = empleado.empresa_id
                self.stdout.write("")
                self.stdout.write(self.style.HTTP_INFO(f"--- {empleado.empresa.nombre} ---"))

            nombre_esperado = f"Sueldo {empleado.nombre}"

            cuentas_qs = TipoGasto.objects.filter(
                empresa=empleado.empresa,
                subgrupo__grupo__nombre="Gastos Nomina",
                subgrupo__nombre="Sueldos y salarios",
            )
            nombres_existentes = list(cuentas_qs.values_list("id", "nombre"))

            if any(nombre == nombre_esperado for _, nombre in nombres_existentes):
                continue  # ya coincide exacto, nada que hacer

            palabras_empleado = set(empleado.nombre.upper().split())
            candidatos = []
            for cuenta_id, nombre in nombres_existentes:
                palabras_cuenta = set(nombre.replace("Sueldo ", "", 1).upper().split())
                if palabras_cuenta and palabras_cuenta.issubset(palabras_empleado):
                    candidatos.append((cuenta_id, nombre))

            if len(candidatos) == 1:
                cuenta_id, nombre_viejo = candidatos[0]
                self.stdout.write(f"  \"{nombre_viejo}\"  ->  \"{nombre_esperado}\"")
                if aplicar:
                    with transaction.atomic():
                        TipoGasto.objects.filter(id=cuenta_id).update(nombre=nombre_esperado)
                renombrados += 1
            elif len(candidatos) > 1:
                ambiguos += 1
                self.stdout.write(self.style.WARNING(
                    f"  AMBIGUO -- {empleado.nombre}: varias cuentas posibles {[n for _, n in candidatos]} -- revisa a mano, no se toco."
                ))
            else:
                sin_cambio += 1

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS(f"{renombrados} cuenta(s) {'renombrada(s)' if aplicar else 'que se renombrarian con --aplicar'}."))
        if ambiguos:
            self.stdout.write(self.style.ERROR(f"{ambiguos} caso(s) ambiguo(s) -- revisalos manualmente, no se tocaron."))
        self.stdout.write(f"{sin_cambio} empleado(s) sin cuenta previa relacionada (normal si nunca han cobrado).")

        if not aplicar and renombrados:
            self.stdout.write("")
            self.stdout.write(self.style.WARNING("Nada se guardo todavia -- vuelve a correr con --aplicar cuando confirmes que la lista se ve bien."))