"""Crea (o reutiliza) una empresa DEMO del segmento 'arrendamiento' con datos de ejemplo.

Idempotente. Los valores de INPC son FICTICIOS (fuente "DEMO"); no los uses para cobrar.
Uso:  python manage.py sembrar_demo_leasing --usuario TU_USUARIO
"""
from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from empresas.models import Empresa
from leasing.models import (
    ConceptoCobro,
    Contraparte,
    Contrato,
    ContratoUnidad,
    ContratoVersion,
    Escalador,
    IndiceValor,
    Inmueble,
    RelacionMaestroSub,
    TerminoFinanciero,
    Unidad,
)
from leasing.services.calendario import generar_calendario
from principal.models import PerfilUsuario


class Command(BaseCommand):
    help = "Crea una empresa DEMO de arrendamiento con inmueble, contratos, subarriendo y calendario."

    def add_arguments(self, parser):
        parser.add_argument("--usuario", help="Username al que se asigna la empresa demo (perfil).")
        parser.add_argument("--hasta", default="2027-12-31", help="Fin del calendario (YYYY-MM-DD).")

    @transaction.atomic
    def handle(self, *a, **o):
        emp, _ = Empresa.objects.get_or_create(
            nombre="DEMO Arrendamientos",
            defaults={"rfc": "DEM010101AA1", "direccion": "Dirección de prueba", "segmento": "arrendamiento"},
        )
        if emp.segmento != "arrendamiento":
            raise CommandError("Existe una empresa 'DEMO Arrendamientos' que no es del segmento arrendamiento.")

        inm, _ = Inmueble.objects.get_or_create(
            empresa=emp, clave="DEMO-01", defaults={"nombre": "Plaza Demo", "entidad_federativa": "CDMX"}
        )
        local, _ = Unidad.objects.get_or_create(
            empresa=emp, inmueble=inm, clave="L-101", defaults={"m2_rentables": Decimal("120")}
        )
        conc, _ = ConceptoCobro.objects.get_or_create(empresa=emp, clave="RENTA", defaults={"nombre": "Renta"})

        for ym, v in ((date(2025, 12, 1), "100.000000"), (date(2026, 12, 1), "104.500000")):
            IndiceValor.objects.get_or_create(
                indice="INPC", periodo=ym, defaults={"valor": Decimal(v), "fuente": "DEMO (ficticio)"}
            )

        def contrato(folio, rol, inicio, fin, subarr="NO"):
            c, creado = Contrato.objects.get_or_create(empresa=emp, folio=folio, defaults={"rol": rol})
            if creado:
                v = ContratoVersion(
                    empresa=emp, contrato=c, numero=1, fecha_efectiva=inicio, fecha_inicio=inicio,
                    fecha_fin=fin, subarriendo_permitido=subarr,
                )
                v.full_clean()
                v.save()
                v.marcar_vigente()
            return c, c.versiones.get(es_vigente=True)

        maestro, vm = contrato("DEMO-M01", "EGRESO", date(2026, 1, 1), date(2030, 12, 31), "GENERAL")
        ContratoUnidad.objects.get_or_create(
            empresa=emp, version=vm, unidad=local, defaults={"m2_asignados": Decimal("120")}
        )
        sub, vs = contrato("DEMO-S01", "SUBARRIENDO", date(2026, 6, 1), date(2029, 12, 31))
        if not RelacionMaestroSub.objects.filter(sub=sub).exists():
            RelacionMaestroSub.objects.create(
                empresa=emp, sub=sub, maestro=maestro, m2_asignados=Decimal("60"),
                tipo_consentimiento="GENERAL",
            )
        ingreso, vi = contrato("DEMO-I01", "INGRESO", date(2026, 1, 1), date(2030, 12, 31))

        total = 0
        for v, monto, folio in ((vi, "10000", "DEMO-I01"), (vs, "6000", "DEMO-S01"), (vm, "8000", "DEMO-M01")):
            t, creado = TerminoFinanciero.objects.get_or_create(
                empresa=emp, version=v, concepto=conc,
                defaults={"monto": Decimal(monto), "dia_vencimiento": 5, "fecha_inicio": v.fecha_inicio},
            )
            if creado:
                Escalador.objects.create(
                    empresa=emp, termino=t, tipo="INPC", aplicar_desde=date(2027, v.fecha_inicio.month, 1),
                    rezago_meses=1, tope_pct=Decimal("8"),
                )
            r = generar_calendario(t, date.fromisoformat(o["hasta"]))
            total += r.creadas
            self.stdout.write(f"{folio}: {r}")
            for p in r.pendientes:
                self.stdout.write(self.style.WARNING("  PENDIENTE: " + p))

        if o.get("usuario"):
            try:
                user = get_user_model().objects.get(username=o["usuario"])
            except get_user_model().DoesNotExist as e:
                raise CommandError(f"No existe el usuario {o['usuario']!r}.") from e
            PerfilUsuario.objects.update_or_create(usuario=user, defaults={"empresa": emp})
            self.stdout.write(f"Usuario {user.username} ahora apunta a la empresa DEMO (id={emp.pk}).")
        self.stdout.write(self.style.SUCCESS(f"Listo. Empresa DEMO id={emp.pk}; partidas nuevas: {total}."))
