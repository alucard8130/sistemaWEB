"""Reaplica las reglas de rubro / fondo de efectivo a los ingresos de Academic+ ya
importados. Util cuando se agrega una regla nueva (p. ej. 'blusa' = uniformes):
corrige el rubro 'Sin clasificar' y pasa el efectivo de IPC al fondo que le
corresponde. No toca fondos que ya gastaron ese dinero (los lista).

    python manage.py reclasificar_ingresos_escuela --dry-run
    python manage.py reclasificar_ingresos_escuela
"""
import datetime
from collections import defaultdict
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction

from caja_chica.models import FondeoCajaChica
from escuelas.ingresos_utils import (
    RUBRO_SIN_CLASIFICAR,
    categoria_fondo,
    normalizar_rubro,
    numero_fondeo_efectivo,
)
from escuelas.models import IngresoEscuela

CERO = Decimal('0.00')


class Command(BaseCommand):
    help = 'Corrige rubro y fondo de efectivo (IPC) de ingresos ya importados.'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='Solo muestra lo que haria.')

    def handle(self, *args, **opts):
        dry = opts['dry_run']
        base = IngresoEscuela.objects.exclude(origen='manual')

        # 1) Rubro: solo los que estaban sin clasificar y ahora si tienen regla.
        cambios_rubro = defaultdict(list)
        for ing in base.filter(rubro__in=['', RUBRO_SIN_CLASIFICAR]).only('id', 'concepto', 'rubro'):
            nuevo = normalizar_rubro(ing.concepto)
            if nuevo != RUBRO_SIN_CLASIFICAR and nuevo != ing.rubro:
                cambios_rubro[nuevo].append(ing.pk)
        for rubro, ids in sorted(cambios_rubro.items()):
            self.stdout.write(f'Rubro -> {rubro}: {len(ids)} cobro(s)')
            if not dry:
                IngresoEscuela.objects.filter(pk__in=ids).update(rubro=rubro)

        # 2) Fondo de efectivo de IPC: cada cobro debe estar en el fondo de su categoria.
        movimientos = defaultdict(lambda: {'total': CERO, 'ids': [], 'fecha': datetime.date.min})
        qs = base.filter(es_efectivo=True, fuente='ipc', fondeo__isnull=False).select_related('fondeo')
        for ing in qs:
            esperado = numero_fondeo_efectivo('ipc', ing.fecha.year, ing.fecha.month, categoria_fondo(ing.concepto))
            if ing.fondeo.numero_cheque != esperado:
                m = movimientos[(ing.fondeo_id, ing.empresa_id, esperado)]
                m['total'] += ing.monto
                m['ids'].append(ing.pk)
                m['fecha'] = max(m['fecha'], ing.fecha)
        for (fondeo_id, empresa_id, esperado), m in sorted(movimientos.items(), key=lambda kv: kv[0][2]):
            origen = FondeoCajaChica.objects.get(pk=fondeo_id)
            self.stdout.write(f'Caja {origen.numero_cheque} -> {esperado}: ${m["total"]:,.2f} ({len(m["ids"])} cobro(s))')
            if dry:
                continue
            with transaction.atomic():
                origen = FondeoCajaChica.objects.select_for_update().get(pk=fondeo_id)
                if origen.saldo < m['total']:
                    self.stdout.write(self.style.WARNING(
                        f'   OMITIDO: {origen.numero_cheque} ya gasto parte de ese efectivo '
                        f'(saldo ${origen.saldo:,.2f}).'))
                    continue
                destino = FondeoCajaChica.objects.select_for_update().filter(
                    empresa_id=empresa_id, numero_cheque=esperado).first()
                if destino is None:
                    destino = FondeoCajaChica.objects.create(
                        empresa_id=empresa_id, numero_cheque=esperado, importe_cheque=CERO, saldo=CERO,
                        fecha=m['fecha'], origen='cobros_efectivo', fuente='ipc',
                        empleado_asignado=None, cuenta_bancaria=None,
                    )
                destino.importe_cheque += m['total']
                destino.saldo += m['total']
                destino.fecha = max(destino.fecha, m['fecha'])
                destino.save()
                IngresoEscuela.objects.filter(pk__in=m['ids']).update(fondeo=destino)
                origen.importe_cheque -= m['total']
                origen.saldo -= m['total']
                if origen.importe_cheque <= 0 and not origen.gastocajachica_set.exists() and not origen.valecaja_set.exists():
                    origen.delete()
                else:
                    origen.save()
        if not cambios_rubro and not movimientos:
            self.stdout.write('Nada que corregir.')
        self.stdout.write(self.style.SUCCESS('Listo.' + (' (dry-run, sin cambios)' if dry else '')))
