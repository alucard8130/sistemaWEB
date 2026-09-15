
from datetime import datetime
from decimal import Decimal, InvalidOperation

import openpyxl
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import redirect, render

from .models import IngresoEscuela


@login_required
def importar_ingresos_excel(request):
    perfil = getattr(request.user, 'perfilusuario', None)
    if not perfil or not perfil.empresa:
        messages.error(request, "No tienes una empresa asociada.")
        return redirect('dashboard_inicio')

    if request.method == 'POST':
        archivo = request.FILES.get('archivo_excel')
        if not archivo:
            messages.error(request, "Selecciona un archivo Excel.")
            return redirect('importar_ingresos_excel')

        try:
            wb = openpyxl.load_workbook(archivo, data_only=True)
            hoja = wb.active
        except Exception as e:  # noqa: BLE001
            messages.error(request, f"No se pudo leer el archivo -- verifica que sea un Excel válido ({e}).")
            return redirect('importar_ingresos_excel')

        filas = list(hoja.iter_rows(min_row=2, values_only=True))
        creados = 0
        errores = []
        categorias_validas = dict(IngresoEscuela.CATEGORIA_CHOICES)

        with transaction.atomic():
            for i, fila in enumerate(filas, start=2):
                if not fila or all(celda is None for celda in fila):
                    continue

                fila_completa = (list(fila) + [None, None, None, None])[:4]
                fecha_raw, concepto, categoria_raw, monto_raw = fila_completa

                if not fecha_raw or not concepto or monto_raw is None:
                    errores.append(f"Fila {i}: faltan datos obligatorios (fecha, concepto, o monto).")
                    continue

                if isinstance(fecha_raw, datetime):
                    fecha = fecha_raw.date()
                else:
                    try:
                        fecha = datetime.strptime(str(fecha_raw).strip(), '%Y-%m-%d').date()  # noqa: DTZ007
                    except ValueError:
                        errores.append(f"Fila {i}: fecha '{fecha_raw}' no es válida (usa AAAA-MM-DD).")
                        continue

                try:
                    monto = Decimal(str(monto_raw))
                except (InvalidOperation, TypeError):
                    errores.append(f"Fila {i}: monto '{monto_raw}' no es válido.")
                    continue

                if monto <= 0:
                    errores.append(f"Fila {i}: el monto debe ser mayor a $0.")
                    continue

                categoria = str(categoria_raw).strip().lower() if categoria_raw else 'otro'
                if categoria not in categorias_validas:
                    categoria = 'otro'

                IngresoEscuela.objects.create(
                    empresa=perfil.empresa,
                    fecha=fecha,
                    concepto=str(concepto).strip(),
                    categoria=categoria,
                    monto=monto,
                    importado_por=request.user,
                    archivo_origen=archivo.name,
                )
                creados += 1

        if creados:
            messages.success(request, f"Se importaron {creados} ingreso(s) correctamente.")
        if errores:
            mensaje_errores = " | ".join(errores[:10])
            if len(errores) > 10:
                mensaje_errores += f" ... y {len(errores) - 10} más."
            messages.warning(request, f"{len(errores)} fila(s) con errores, se omitieron: {mensaje_errores}")
        if not creados and not errores:
            messages.warning(request, "El archivo no tenía filas con datos para importar.")

        return redirect('importar_ingresos_excel')

    ingresos_recientes = IngresoEscuela.objects.filter(empresa=perfil.empresa)[:20]
    return render(request, 'escuelas/importar_ingresos.html', {
        'ingresos_recientes': ingresos_recientes,
    })
