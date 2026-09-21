from datetime import date

from django.db.models import Q

from .models import IngresoEscuela


def calcular_metricas_alumnos(empresa, fecha_referencia=None):
    """Calcula metricas de alumnos a partir del historico de IngresoEscuela
    -- solo cuenta matriculas capturadas (ambos importadores ya las
    guardan). No sustituye un reporte real de bajas -- 'en riesgo de baja'
    es una aproximacion basada en pagos de colegiatura ausentes.

    fecha_referencia (opcional) -- calcula las metricas COMO SI fuera ese
    mes (dia 1 de un mes cualquiera), en vez de con la fecha de hoy. Util
    para revisar meses anteriores. Por default usa hoy."""
    if fecha_referencia is None:
        fecha_referencia = date.today()

    matriculas_base = (
        IngresoEscuela.objects.filter(empresa=empresa, matricula__isnull=False)
        .exclude(matricula='')
    )

    alumnos_activos_mes = (
        matriculas_base.filter(
            categoria='colegiatura',
            fecha__year=fecha_referencia.year, fecha__month=fecha_referencia.month,
        ).values_list('matricula', flat=True).distinct().count()
    )

    todas_las_matriculas = matriculas_base.values_list('matricula', flat=True).distinct()
    alumnos_nuevos = 0
    for matricula in todas_las_matriculas:
        primer_registro = (
            IngresoEscuela.objects.filter(empresa=empresa, matricula=matricula)
            .order_by('fecha').first()
        )
        if (
            primer_registro
            and primer_registro.categoria == 'inscripcion'
            and primer_registro.fecha.year == fecha_referencia.year
            and primer_registro.fecha.month == fecha_referencia.month
        ):
            alumnos_nuevos += 1

    mes_1 = fecha_referencia.month - 1 or 12
    anio_1 = fecha_referencia.year if fecha_referencia.month > 1 else fecha_referencia.year - 1
    mes_2 = mes_1 - 1 or 12
    anio_2 = anio_1 if mes_1 > 1 else anio_1 - 1

    fecha_limite_historial = date(anio_2, mes_2, 1)
    matriculas_con_historial_previo = set(
        matriculas_base.filter(categoria='colegiatura', fecha__lt=fecha_limite_historial)
        .values_list('matricula', flat=True).distinct()
    )
    matriculas_pagaron_recientemente = set(
        matriculas_base.filter(categoria='colegiatura')
        .filter(Q(fecha__year=anio_1, fecha__month=mes_1) | Q(fecha__year=anio_2, fecha__month=mes_2))
        .values_list('matricula', flat=True).distinct()
    )
    en_riesgo_baja = matriculas_con_historial_previo - matriculas_pagaron_recientemente

    total_alumnos_historicos = (
        matriculas_base.filter(categoria='colegiatura')
        .values_list('matricula', flat=True).distinct().count()
    )

    return {
        'alumnos_activos_mes': alumnos_activos_mes,
        'alumnos_nuevos_mes': alumnos_nuevos,
        'alumnos_en_riesgo_baja': len(en_riesgo_baja),
        'total_alumnos_historicos': total_alumnos_historicos,
    }