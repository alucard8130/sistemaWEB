# ============================================================
#
# Cada vez que se registra un Pago real, revisa si el cliente tiene
# un Plan de Pago activo -- si el monto del pago coincide EXACTO (con
# tolerancia de centavos por redondeo) con la SIGUIENTE parcialidad
# pendiente, la marca como pagada y la vincula a ese Pago.
#
# Si no hay un match claro (monto distinto, sin plan activo, etc.), NO
# hace nada -- es mejor dejarlo para revisión manual (ya existe el botón
# de "marcar como pagada" a mano en detalle_plan_pago) que vincular algo
# incorrecto y dar una falsa sensación de que el plan va al corriente.
# ============================================================

from decimal import Decimal

from django.db.models.signals import post_save
from django.dispatch import receiver

from gestion_cobranza.models import (
    ExpedienteCobranza,
    GestionCobranza,
    ParcialidadPlanPago,
)

TOLERANCIA_CENTAVOS = Decimal("0.02")


def vincular_pago_con_parcialidad(pago):
    if not pago.factura_id or not pago.factura.cliente_id:
        return
    expediente = ExpedienteCobranza.objects.filter(
        empresa=pago.factura.empresa, cliente=pago.factura.cliente, estatus='activo',
    ).first()
    if not expediente:
        return
    siguiente_parcialidad = ParcialidadPlanPago.objects.filter(
        plan__expediente=expediente, plan__estatus='activo', estatus='pendiente',
    ).order_by('numero').first()
    if not siguiente_parcialidad:
        return

    if abs(Decimal(str(pago.monto)) - siguiente_parcialidad.monto) > TOLERANCIA_CENTAVOS:
        return  # el monto no coincide -- no se adivina, se deja para revisión manual

    siguiente_parcialidad.estatus = 'pagada'
    siguiente_parcialidad.fecha_pago = pago.fecha_pago
    siguiente_parcialidad.pago = pago
    siguiente_parcialidad.save(update_fields=['estatus', 'fecha_pago', 'pago'])

    siguiente_parcialidad.plan.actualizar_estatus()

    GestionCobranza.objects.create(
        expediente=expediente, tipo_gestion="nota", resultado="promesa_pago",
        notas=(
            f"Parcialidad {siguiente_parcialidad.numero}/{siguiente_parcialidad.plan.numero_parcialidades} "
            f"vinculada automáticamente al registrar el pago (${pago.monto:,.2f})."
        ),
    )


@receiver(post_save, sender="facturacion.Pago")
def pago_vincular_parcialidad(sender, instance, created, **kwargs):
    if created:
        vincular_pago_con_parcialidad(instance)