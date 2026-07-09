"""Lógica de detección automática de faltas."""
from django.db.models import Q

from .models import Empleado, Incidencia, RegistroAsistencia

# Tipos de incidencia que justifican no haber checado entrada ese día.
# OJO: 'dias festivos' y 'descanso' NO van aquí -- significan que el
# empleado SÍ trabajó ese día (festivo/descanso trabajado), no que estuvo
# ausente con permiso.
TIPOS_QUE_EXCUSAN_FALTA = ['permiso', 'vacaciones', 'incapacidad']


def detectar_y_registrar_faltas(fecha, empresa=None):
    """
    Para la fecha dada, revisa todos los empleados activos (de la empresa
    indicada, o todos si no se especifica) y crea una Incidencia tipo
    'falta' para quien no tenga una entrada registrada ese día -- a menos
    que ya tenga una incidencia que lo justifique (permiso, vacaciones,
    incapacidad) cubriendo esa fecha.

    Devuelve la lista de empleados a los que se les creó una falta nueva
    (no cuenta los que ya la tenían de antes, para evitar reportar
    duplicados en ejecuciones repetidas).
    """
    empleados = Empleado.objects.filter(activo=True)
    if empresa:
        empleados = empleados.filter(empresa=empresa)

    faltas_creadas = []

    for empleado in empleados:
        tiene_entrada = RegistroAsistencia.objects.filter(
            empleado=empleado, fecha=fecha, hora_entrada__isnull=False,
        ).exists()
        if tiene_entrada:
            continue

        tiene_excusa = Incidencia.objects.filter(
            empleado=empleado, tipo__in=TIPOS_QUE_EXCUSAN_FALTA, fecha__lte=fecha,
        ).filter(
            Q(fecha_fin__gte=fecha) | Q(fecha_fin__isnull=True, fecha=fecha)
        ).exists()
        if tiene_excusa:
            continue

        incidencia, creada = Incidencia.objects.get_or_create(
            empleado=empleado,
            tipo='falta',
            fecha=fecha,
            defaults={'descripcion': 'Falta detectada automáticamente: no se registró entrada ese día.'}
        )
        if creada:
            faltas_creadas.append(empleado)

    return faltas_creadas