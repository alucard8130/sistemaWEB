import calendar
from datetime import date

from dateutil.relativedelta import relativedelta
from django.core.management.base import BaseCommand
from django.db import transaction

from areas.models import AreaComun
from arrendamientos.models import ContratoArea


class Command(BaseCommand):
    help = (
        "Migra areas comunes ya ocupadas (datos de produccion capturados "
        "antes del modulo de Contratos) creandoles un ContratoArea "
        "retroactivo. Si la fecha_fin (real o corregida) ya paso, el "
        "contrato se crea directamente como 'vencido_ocupado' y se "
        "extiende hasta el fin del mes actual -- para que el mes "
        "siguiente el flujo normal de facturacion/cron lo siga tomando "
        "sin intervencion. Es idempotente."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run', action='store_true',
            help="Solo muestra que se crearia, sin guardar nada en la base de datos."
        )
        parser.add_argument(
            '--empresa-id', type=int, default=None,
            help="Limita la migracion a una sola empresa (por su id). Si se omite, corre sobre todas."
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        empresa_id = options['empresa_id']
        hoy = date.today()
        ultimo_dia_mes_actual = calendar.monthrange(hoy.year, hoy.month)[1]
        fin_de_mes_actual = date(hoy.year, hoy.month, ultimo_dia_mes_actual)

        areas_a_migrar = AreaComun.objects.filter(
            activo=True, cliente__isnull=False,
        ).exclude(
            contratos__estatus__in=['vigente', 'vencido_ocupado']
        )

        if empresa_id:
            areas_a_migrar = areas_a_migrar.filter(empresa_id=empresa_id)

        creados = 0
        con_advertencia = 0

        for area in areas_a_migrar:
            advertencias = []

            fecha_inicio = area.fecha_inicial
            if not fecha_inicio:
                self.stdout.write(self.style.WARNING(
                    f"  [OMITIDA] Área {area.numero}: no tiene fecha_inicial capturada -- revisar a mano."
                ))
                continue

            fecha_fin = area.fecha_fin
            if not fecha_fin:
                fecha_fin = fecha_inicio + relativedelta(years=1)
                advertencias.append(f"sin fecha_fin -- se calculó {fecha_fin} (1 año) como base")
            elif fecha_fin >= fecha_inicio + relativedelta(years=10):
                fecha_fin_original = fecha_fin
                fecha_fin = fecha_inicio + relativedelta(years=1)
                advertencias.append(
                    f"fecha_fin original ({fecha_fin_original}) implica 10 años o más -- "
                    f"probable placeholder de 'indefinido', se calculó {fecha_fin} (1 año) como base"
                )

            if fecha_fin <= fecha_inicio:
                fecha_fin = fecha_inicio + relativedelta(years=1)
                advertencias.append(f"fecha_fin inválida (<= inicio) -- se corrigió a {fecha_fin} como base")

            if fecha_fin < hoy:
                estatus_migrado = 'vencido_ocupado'
                fecha_fin_final = fin_de_mes_actual
                advertencias.append(
                    f"ya estaba vencido bajo el sistema viejo (fecha_fin calculada: {fecha_fin}) -- "
                    f"migrado como vencido_ocupado, extendido hasta {fecha_fin_final} "
                    f"(la facturación del mes siguiente ya sale del flujo nuevo)"
                )
            else:
                estatus_migrado = 'vigente'
                fecha_fin_final = fecha_fin

            if area.es_cuota_variable:
                advertencias.append(
                    "tenía es_cuota_variable=True -- se migró como renta FIJA "
                    "(no hay % de ventas que migrar); revisa si debe ser variable/mixta"
                )

            periodicidad = 'anual' if area.es_cuota_anual else 'mensual'

            if advertencias:
                con_advertencia += 1
                for msg in advertencias:
                    self.stdout.write(self.style.WARNING(f"  [AVISO] Área {area.numero}: {msg}"))

            if not dry_run:
                with transaction.atomic():
                    ContratoArea.objects.create(
                        area=area,
                        cliente=area.cliente,
                        giro=area.giro,
                        fecha_firma=fecha_inicio,
                        fecha_inicio=fecha_inicio,
                        fecha_fin=fecha_fin_final,
                        cuota=area.cuota,
                        deposito=area.deposito,
                        periodicidad_facturacion=periodicidad,
                        tipo_renta='fija',
                        estatus=estatus_migrado,
                    )

            creados += 1
            etiqueta = '(simulado) ' if dry_run else ''
            self.stdout.write(
                f"  Área {area.numero}: contrato {etiqueta}creado [{estatus_migrado}] -- "
                f"{area.cliente.nombre}, ${area.cuota}, {fecha_inicio} a {fecha_fin_final}"
            )

        self.stdout.write("")
        if dry_run:
            self.stdout.write(self.style.SUCCESS(
                f"SIMULACRO: se crearían {creados} contrato(s), {con_advertencia} con avisos a revisar. "
                f"Nada se guardó -- corre sin --dry-run para aplicar de verdad."
            ))
        else:
            self.stdout.write(self.style.SUCCESS(
                f"{creados} contrato(s) creado(s), {con_advertencia} con avisos a revisar manualmente."
            ))