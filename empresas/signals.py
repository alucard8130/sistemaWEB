from django.db import transaction
from django.db.models import Q
from django.db.models.signals import post_save
from django.dispatch import receiver

from acceso_empresas.models import AccesoEmpresa, AlertaGesac
from caja_chica.models import FondeoCajaChica
from empresas.models import CuentaBancaria
from facturacion.models import CobroOtrosIngresos, Pago
from gastos.models import Gasto, PagoGasto


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


@receiver(post_save, sender=CuentaBancaria)
def backfill_primera_cuenta_bancaria(sender, instance, created, **kwargs):
    if not created:
        return

    poblar_cuenta_bancaria_inicial(
        instance,
        sobrescribir=False,
        solo_si_primera=True,
    )



# ===============================================
# acceso_empresas/signals.py (archivo nuevo),
# en acceso_empresas/apps.py, dentro de ready():
#     import acceso_empresas.signals


@receiver(post_save, sender=Gasto)
def crear_alerta_gasto_alto(sender, instance, created, **kwargs):
    """Al crear un Gasto por encima del umbral configurado en la empresa
    (sin importar si vino de captura manual o de Dispersion de Nomina),
    avisa a cada usuario del portal que tenga 'recibir_alertas_gastos'
    activado para esa empresa."""
    if not created:
        return
    if instance.monto is None:
        return
    if not instance.empresa_id:
        return

    # El umbral es por empresa, no un numero fijo global.
    umbral = instance.empresa.umbral_alerta_gastos
    if umbral is None or instance.monto <= umbral:
        return

    accesos = AccesoEmpresa.objects.filter(
        empresa_id=instance.empresa_id, activo=True, recibir_alertas_gastos=True,
    ).select_related("usuario_acceso")

    if not accesos:
        return

    proveedor_o_empleado = (
        instance.proveedor.nombre if instance.proveedor
        else instance.empleado.nombre if instance.empleado
        else "Sin proveedor/empleado"
    )
    mensaje = (
        f"Nueva solicitud de gasto por ${instance.monto:,.2f} "
        f"({proveedor_o_empleado})"
        + (f" -- {instance.tipo_gasto.nombre}" if instance.tipo_gasto_id else "")
    )

    alertas_nuevas = [
        AlertaGesac(
            usuario_acceso=acceso.usuario_acceso,
            empresa_id=instance.empresa_id,
            mensaje=mensaje,
            gasto_id=instance.id,
        )
        for acceso in accesos
    ]
    AlertaGesac.objects.bulk_create(alertas_nuevas)