# ============================================================
# Colocalo en: cualquier_app/templatetags/membresia_extras.py
# (crea la carpeta templatetags/ con un __init__.py vacio si no
# existe ya en esa app)
# ============================================================

from datetime import timedelta

from django import template
from django.utils import timezone

register = template.Library()


@register.filter
def estado_membresia(fecha_vencimiento):
    """Regresa 'vigente', 'vence_pronto' (7 dias o menos), 'vencida', o
    'sin_fecha' -- mismo criterio que usa el Panorama de Membresias."""
    if not fecha_vencimiento:
        return 'sin_fecha'
    ahora = timezone.now()
    if fecha_vencimiento < ahora:
        return 'vencida'
    elif fecha_vencimiento <= ahora + timedelta(days=7):
        return 'vence_pronto'
    else:
        return 'vigente'