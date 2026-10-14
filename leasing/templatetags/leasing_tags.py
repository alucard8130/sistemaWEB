from datetime import date

from django import template

register = template.Library()

_BADGES = {
    # contrato
    "BORRADOR": "lc-b-gris", "ACTIVO": "lc-b-ok", "EN_RENOVACION": "lc-b-aviso", "TERMINADO": "lc-b-gris",
    # partida
    "PROYECTADA": "lc-b-info", "APROBADA": "lc-b-ok", "FACTURADA": "lc-b-ok", "COBRADA": "lc-b-ok",
    "CANCELADA": "lc-b-gris",
    # incidencia / obligación
    "ABIERTA": "lc-b-aviso", "EN_PROCESO": "lc-b-info", "CERRADA": "lc-b-gris",
    "PENDIENTE": "lc-b-aviso", "CUMPLIDA": "lc-b-ok", "VENCIDA": "lc-b-alerta",
    # prioridad
    "BAJA": "lc-b-gris", "MEDIA": "lc-b-info", "ALTA": "lc-b-aviso", "URGENTE": "lc-b-alerta",
    # rol
    "INGRESO": "lc-b-info", "EGRESO": "lc-b-marca", "SUBARRIENDO": "lc-b-acento",
}


@register.filter
def badge(valor):
    return _BADGES.get(valor, "lc-b-gris")


@register.filter
def dias_hasta(fecha):
    """Días entre hoy y ``fecha`` (negativo si ya pasó)."""
    if not fecha:
        return None
    return (fecha - date.today()).days


@register.filter
def pct(parte, total):
    try:
        return min(100, round(float(parte) * 100 / float(total)))
    except (TypeError, ValueError, ZeroDivisionError):
        return 0


_ROL = {"INGRESO": "Ingreso", "EGRESO": "Egreso", "SUBARRIENDO": "Subarriendo"}


@register.filter
def rol_corto(valor):
    return _ROL.get(valor, valor)
