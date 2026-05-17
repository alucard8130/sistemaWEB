from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver
from caja_chica.models import FondeoCajaChica
from empresas.models import CuentaBancaria
from facturacion.models import Pago, CobroOtrosIngresos
from gastos.models import PagoGasto
from django.db.models import Q


@transaction.atomic
def poblar_cuenta_bancaria_inicial(
    cuenta_bancaria,
    sobrescribir=False,
    solo_si_primera=False,
):
    empresa = cuenta_bancaria.empresa

    if solo_si_primera and CuentaBancaria.objects.filter(empresa=empresa).count() != 1:
        return {
            "pago": 0,
            "cobro_otros_ingresos": 0,
            "pago_gasto": 0,
            "fondeo_caja_chica": 0,
        }

    pago_filter = Q(empresa=empresa) | Q(factura__empresa=empresa)
    cobro_filter = {"factura__empresa": empresa}
    pago_gasto_filter = {"gasto__empresa": empresa}
    fondeo_filter = {"empresa": empresa}

    if not sobrescribir:
        pago_actualizados = Pago.objects.filter(
            pago_filter,
            cuenta_bancaria__isnull=True,
        ).update(cuenta_bancaria=cuenta_bancaria)

        cobro_filter["cuenta_bancaria__isnull"] = True
        pago_gasto_filter["cuenta_bancaria__isnull"] = True
        fondeo_filter["cuenta_bancaria__isnull"] = True
    else:
        pago_actualizados = Pago.objects.filter(
            pago_filter,
        ).update(cuenta_bancaria=cuenta_bancaria)

    return {
        "pago": pago_actualizados,
        "cobro_otros_ingresos": CobroOtrosIngresos.objects.filter(
            **cobro_filter
        ).update(cuenta_bancaria=cuenta_bancaria),
        "pago_gasto": PagoGasto.objects.filter(**pago_gasto_filter).update(
            cuenta_bancaria=cuenta_bancaria
        ),
        "fondeo_caja_chica": FondeoCajaChica.objects.filter(**fondeo_filter).update(
            cuenta_bancaria=cuenta_bancaria
        ),
    }


# def poblar_cuenta_bancaria_inicial(cuenta_bancaria):
#     empresa = cuenta_bancaria.empresa

#     # Solo se autopuebla si es la primera cuenta bancaria de la empresa.
#     # Si ya hay varias, ya no es seguro decidir cuál corresponde.
#     if CuentaBancaria.objects.filter(empresa=empresa).count() != 1:
#         return

#     Pago.objects.filter(
#         factura__empresa=empresa,
#         cuenta_bancaria__isnull=True,
#     ).update(cuenta_bancaria=cuenta_bancaria)

#     CobroOtrosIngresos.objects.filter(
#         factura__empresa=empresa,
#         cuenta_bancaria__isnull=True,
#     ).update(cuenta_bancaria=cuenta_bancaria)

#     PagoGasto.objects.filter(
#         gasto__empresa=empresa,
#         cuenta_bancaria__isnull=True,
#     ).update(cuenta_bancaria=cuenta_bancaria)

#     FondeoCajaChica.objects.filter(
#         empresa=empresa,
#         cuenta_bancaria__isnull=True,
#     ).update(cuenta_bancaria=cuenta_bancaria)


@receiver(post_save, sender=CuentaBancaria)
def backfill_primera_cuenta_bancaria(sender, instance, created, **kwargs):
    if not created:
        return

    poblar_cuenta_bancaria_inicial(
        instance,
        sobrescribir=False,
        solo_si_primera=True,
    )


# def backfill_primera_cuenta_bancaria(sender, instance, created, **kwargs):
#     if not created:
#         return

#     empresa = instance.empresa

#     # Solo autopoblar si es la primera cuenta bancaria de la empresa
#     if CuentaBancaria.objects.filter(empresa=empresa).count() != 1:
#         return

#     with transaction.atomic():
#         Pago.objects.filter(
#             empresa=empresa,
#             factura__empresa=empresa,
#             cuenta_bancaria__isnull=True,
#         ).update(cuenta_bancaria=instance)

#         CobroOtrosIngresos.objects.filter(
#             factura__empresa=empresa,
#             cuenta_bancaria__isnull=True,
#         ).update(cuenta_bancaria=instance)

#         PagoGasto.objects.filter(
#             gasto__empresa=empresa,
#             cuenta_bancaria__isnull=True,
#         ).update(cuenta_bancaria=instance)

#         FondeoCajaChica.objects.filter(
#             empresa=empresa,
#             cuenta_bancaria__isnull=True,
#         ).update(cuenta_bancaria=instance)
