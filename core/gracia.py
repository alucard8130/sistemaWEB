"""Plazo de gracia de la membresia despues de la fecha de vencimiento.

- GESAC Condominios / Comercial: 4 dias despues de vencer.
- GESAC Campus (escuelas): hasta el dia 15 del mes en que vencio; si vencio
  despues del 15, conserva los 4 dias de gracia de siempre.
"""

import datetime
from datetime import timedelta

from django.utils import timezone

DIAS_GRACIA_BLOQUEO = 4
DIA_LIMITE_GRACIA_ESCUELA = 15


def es_escuela(perfil):
    empresa = getattr(perfil, 'empresa', None)
    return bool(empresa and empresa.segmento == 'escuela')


def limite_gracia(fecha_vencimiento, escuela=False):
    """Fecha y hora (con zona horaria) hasta la que se conserva el acceso.
    Pasado ese momento, la cuenta se bloquea."""
    limite = fecha_vencimiento + timedelta(days=DIAS_GRACIA_BLOQUEO)
    if not escuela:
        return limite
    venc_local = timezone.localtime(fecha_vencimiento)
    dia_limite = timezone.make_aware(datetime.datetime.combine(
        datetime.date(venc_local.year, venc_local.month, DIA_LIMITE_GRACIA_ESCUELA),
        datetime.time(23, 59, 59),
    ))
    return max(limite, dia_limite)
