"""Separa los fondos de efectivo de IPC ya importados (uno por mes) en un fondo
por categoria y mes. Solo toca fondos que no tienen gastos ni vales.

    python manage.py separar_fondos_ipc_por_rubro --dry-run
    python manage.py separar_fondos_ipc_por_rubro
"""
import re
from collections import defaultdict
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction

from caja_chica.models import FondeoCajaChica
from escuelas.ingresos_utils import categoria_fondo, numero_fondeo_efectivo
from escuelas.models import IngresoEscuela

PATRON_VIEJO = re.compile(r'^EFE-IPC-(\d{4})-(\d{2})$')


class Command(BaseCommand):
    help = 'Divide los fondos de efectivo IPC mensuales en un fondo por categoria.'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='Solo muestra lo que haria.')

    def handle(self, *args, **opts):
        dry = opts['dry_run']
        viejos = FondeoCajaChica.objects.filter(
            origen='cobros_efectivo', fuente='ipc', numero_cheque__startswith='EFE-IPC-'
        )
        for fondeo in viejos:
            m = PATRON_VIEJO.match(fondeo.numero_cheque)
            if not m:
                continue
            if fondeo.gastocajachica_set.exists() or fondeo.valecaja_set.exists():
                self.stdout.write(self.style.WARNING(
                    f'{fondeo.numero_cheque}: tiene gastos/vales, no se separa.'))
                continue
            anio, mes = int(m.group(1)), int(m.group(2))
            ingresos = list(IngresoEscuela.objects.filter(fondeo=fondeo))
            por_rubro = defaultdict(list)
            for ing in ingresos:
                por_rubro[categoria_fondo(ing.concepto)].append(ing)
            self.stdout.write(f'{fondeo.numero_cheque}: {len(ingresos)} cobros -> {len(por_rubro)} fondos')
            for rubro, lista in sorted(por_rubro.items()):
                total = sum((i.monto for i in lista), Decimal('0.00'))
                self.stdout.write(f'   {numero_fondeo_efectivo("ipc", anio, mes, rubro)}  ${total:,.2f}  ({len(lista)})')
            if dry:
                continue
            with transaction.atomic():
                for rubro, lista in por_rubro.items():
                    total = sum((i.monto for i in lista), Decimal('0.00'))
                    nuevo, _ = FondeoCajaChica.objects.get_or_create(
                        empresa=fondeo.empresa,
                        numero_cheque=numero_fondeo_efectivo('ipc', anio, mes, rubro),
                        defaults=dict(
                            importe_cheque=Decimal('0.00'), saldo=Decimal('0.00'),
                            fecha=max(i.fecha for i in lista),
                            origen='cobros_efectivo', fuente='ipc',
                            empleado_asignado=None, cuenta_bancaria=None,
                        ),
                    )
                    nuevo.importe_cheque += total
                    nuevo.saldo += total
                    nuevo.fecha = max(nuevo.fecha, max(i.fecha for i in lista))
                    nuevo.save()
                    IngresoEscuela.objects.filter(pk__in=[i.pk for i in lista]).update(fondeo=nuevo)
                fondeo.delete()
        self.stdout.write(self.style.SUCCESS('Listo.' + (' (dry-run, sin cambios)' if dry else '')))
