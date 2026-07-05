# Create your views here.
import json
import base64
import anthropic
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.conf import settings
from .models import SesionEstadoCuenta, MovimientoEstadoCuenta
from empresas.models import CuentaBancaria
from clientes.models import Cliente
from facturacion.models import Factura, Pago, FacturaOtrosIngresos, TipoOtroIngreso
import datetime
import re


def extraer_movimientos_con_claude(pdf_bytes, empresa):
    """Llama a Claude API para extraer los movimientos del PDF"""
    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

    # Obtener referencias de clientes de esta empresa para el matching
    clientes = Cliente.objects.filter(empresa=empresa, activo=True).values(
        'id', 'nombre', 'referencia_pago', 'rfc'
    )
    clientes_json = json.dumps(list(clientes), ensure_ascii=False)

    prompt = f"""Analiza este estado de cuenta bancario mexicano y extrae SOLO los abonos.

Devuelve ÚNICAMENTE JSON válido, sin texto adicional, sin explicaciones:

{{
  "banco": "BBVA|BANORTE|BANAMEX|SANTANDER|BANREGIO|HSBC|otro",
  "numero_cuenta": "número",
  "periodo_inicio": "YYYY-MM-DD",
  "periodo_fin": "YYYY-MM-DD",
  "saldo_inicial": 0.00,
  "saldo_final": 0.00,
  "total_abonos": 0.00,
  "abonos": [
    {{
      "fecha": "YYYY-MM-DD",
      "descripcion": "máximo 80 caracteres",
      "referencia": "referencia corta",
      "monto": 0.00,
      "cliente_id": null,
      "confianza_match": "alta|media|baja|ninguna",
      "razon_match": "máximo 40 caracteres"
    }}
  ]
}}

Clientes de la empresa para matching:
{clientes_json}

Reglas:
- Incluye SOLO abonos (columna ABONOS con valor positivo)
- confianza "alta": la referencia de pago exacta (RF-XXXXX-XXXXXX) aparece en la descripción
- confianza "media": el nombre del cliente coincide claramente en la descripción. Los nombres en el estado de cuenta bancario pueden aparecer en formato "APELLIDO,NOMBRE", "APELLIDO APELLIDO NOMBRE", abreviados o sin acentos. Busca coincidencia parcial por apellido(s) o nombre(s) — si al menos un apellido o el nombre coincide con el cliente, es match medio
- confianza "baja": hay coincidencia parcial débil — solo una palabra del nombre coincide, o el concepto del pago sugiere el cliente (ej: "mantenimiento local D02", "renta febrero local 15")
- confianza "ninguna": no se puede identificar al cliente de ninguna forma
- Normaliza los nombres para comparar: ignora acentos, mayúsculas/minúsculas, comas y guiones
- Si detectas el número de local o área en la descripción, úsalo también para identificar al cliente
"""

    pdf_base64 = base64.standard_b64encode(pdf_bytes).decode('utf-8')

    response = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=16000,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "document",
                        "source": {
                            "type": "base64",
                            "media_type": "application/pdf",
                            "data": pdf_base64,
                        }
                    },
                    {
                        "type": "text",
                        "text": prompt
                    }
                ]
            }
        ]
    )

    texto = response.content[0].text.strip()
    # Limpiar posibles backticks de markdown
    texto = re.sub(r'^```json\s*', '', texto)
    texto = re.sub(r'\s*```$', '', texto)
    # Si el JSON está truncado, intentar repararlo
    try:
        return json.loads(texto)
    except json.JSONDecodeError:
        # Intentar truncar hasta el último objeto completo
        ultimo_corchete = texto.rfind('},')
        if ultimo_corchete > 0:
            texto_reparado = texto[:ultimo_corchete + 1] + ']}'
            try:
                return json.loads(texto_reparado)
            except json.JSONDecodeError:
                pass
        raise


@login_required
def lista_sesiones(request):
    perfil = getattr(request.user, 'perfilusuario', None)
    if request.user.is_superuser:
        sesiones = SesionEstadoCuenta.objects.all()
    else:
        empresa = perfil.empresa if perfil else None
        sesiones = SesionEstadoCuenta.objects.filter(empresa=empresa)

    return render(request, 'cobros_estado_cuenta/lista_sesiones.html', {
        'sesiones': sesiones,
    })

@login_required
def eliminar_sesion(request, pk):
    sesion = get_object_or_404(SesionEstadoCuenta, pk=pk)
    if request.method == 'POST':
        sesion.delete()
        messages.success(request, "Estado de cuenta eliminado correctamente.")
        return redirect('lista_sesiones_estado_cuenta')
    return render(request, 'cobros_estado_cuenta/eliminar_sesion.html', {'sesion': sesion})

@login_required
def subir_estado_cuenta(request):
    perfil = getattr(request.user, 'perfilusuario', None)
    empresa = perfil.empresa if perfil and not request.user.is_superuser else None

    cuentas = CuentaBancaria.objects.filter(empresa=empresa, activa=True) if empresa else CuentaBancaria.objects.none()

    if request.method == 'POST':
        archivo = request.FILES.get('archivo')
        cuenta_id = request.POST.get('cuenta_bancaria_id')

        if not archivo:
            messages.error(request, "Debes subir un archivo PDF.")
            return render(request, 'cobros_estado_cuenta/subir.html', {'cuentas': cuentas})

        if not archivo.name.lower().endswith('.pdf'):
            messages.error(request, "Solo se aceptan archivos PDF.")
            return render(request, 'cobros_estado_cuenta/subir.html', {'cuentas': cuentas})

        cuenta = None
        if cuenta_id:
            cuenta = get_object_or_404(CuentaBancaria, pk=cuenta_id, empresa=empresa)

        # ← Leer bytes ANTES de crear la sesión (antes de que Django mueva el archivo)
        pdf_bytes = archivo.read()
        archivo.seek(0)  # Reposicionar para que Django pueda guardarlo correctamente

        # Crear la sesión
        sesion = SesionEstadoCuenta.objects.create(
            empresa=empresa,
            cuenta_bancaria=cuenta,
            archivo=archivo,
            estado='procesando',
            registrado_por=request.user,
        )

        try:
            # Leer el PDF y enviarlo a Claude
            #pdf_bytes = archivo.read()
            datos = extraer_movimientos_con_claude(pdf_bytes, empresa)

            # Actualizar la sesión con los datos del encabezado
            sesion.banco_detectado = datos.get('banco', '')
            sesion.periodo_inicio = datos.get('periodo_inicio')
            sesion.periodo_fin = datos.get('periodo_fin')
            sesion.saldo_inicial = datos.get('saldo_inicial')
            sesion.saldo_final = datos.get('saldo_final')
            sesion.total_abonos = datos.get('total_abonos')
            sesion.estado = 'listo'
            sesion.save()

            # Crear los movimientos extraídos
            for abono in datos.get('abonos', []):
                cliente = None
                if abono.get('cliente_id'):
                    try:
                        cliente = Cliente.objects.get(pk=abono['cliente_id'], empresa=empresa)
                    except Cliente.DoesNotExist:
                        pass

                fecha_str = abono.get('fecha')
                try:
                    fecha = datetime.date.fromisoformat(fecha_str) if fecha_str else sesion.periodo_inicio
                except Exception:
                    fecha = sesion.periodo_inicio

                MovimientoEstadoCuenta.objects.create(
                    sesion=sesion,
                    fecha=fecha,
                    descripcion=abono.get('descripcion', ''),
                    referencia=abono.get('referencia', ''),
                    monto=abono.get('monto', 0),
                    cliente_detectado=cliente,
                    confianza_match=abono.get('confianza_match', 'ninguna'),
                    razon_match=abono.get('razon_match', ''),
                    estado='pendiente',
                )

            messages.success(
                request,
                f"Estado de cuenta procesado correctamente. "
                f"Se detectaron {len(datos.get('abonos', []))} abonos."
            )
            return redirect('revisar_sesion_estado_cuenta', pk=sesion.pk)

        except Exception as e:
            sesion.estado = 'error'
            sesion.error_detalle = str(e)
            sesion.save()
            messages.error(request, f"Error al procesar el PDF: {str(e)}")
            return redirect('lista_sesiones_estado_cuenta')

    return render(request, 'cobros_estado_cuenta/subir.html', {'cuentas': cuentas})


@login_required
def revisar_sesion(request, pk):
    sesion = get_object_or_404(SesionEstadoCuenta, pk=pk)
    perfil = getattr(request.user, 'perfilusuario', None)
    empresa = perfil.empresa if perfil and not request.user.is_superuser else sesion.empresa

    movimientos = sesion.movimientos.all()
    clientes = Cliente.objects.filter(empresa=empresa, activo=True)
    tipos_ingreso = TipoOtroIngreso.objects.filter(empresa=empresa)

    # Facturas pendientes por cliente (cuotas + otros ingresos)
    facturas_por_cliente = {}
    for cliente in clientes:
        lista = []
        # Facturas de cuota pendientes
        for f in Factura.objects.filter(
            cliente=cliente, empresa=empresa, estatus='pendiente', activo=True
        ).order_by('-fecha_vencimiento')[:10]:
            lista.append({
                'id': f.id,
                'tipo': 'cuota',
                'folio': f.folio,
                'concepto': f.get_tipo_cuota_display(),
                'monto': float(f.saldo_pendiente),
                'vencimiento': str(f.fecha_vencimiento),
                'local': f.local.numero if f.local else None,
                'area': f.area_comun.numero if f.area_comun else None,
            })
        # FacturaOtrosIngresos pendientes
        for f in FacturaOtrosIngresos.objects.filter(
            cliente=cliente, empresa=empresa, estatus='pendiente', activo=True
        ).order_by('-fecha_vencimiento')[:10]:
            lista.append({
                'id': f.id,
                'tipo': 'otros',
                'folio': f.folio,
                'concepto': f.tipo_ingreso.nombre if f.tipo_ingreso else 'Otro ingreso',
                'monto': float(f.saldo),
                'vencimiento': str(f.fecha_vencimiento),
                'local': None,
                'area': None,
            })
        if lista:
            facturas_por_cliente[cliente.id] = lista

    # Propiedades por cliente
    from facturacion.models import LocalComercial
    from areas.models import AreaComun as AreaComunModel
    propiedades_por_cliente = {}
    for cliente in clientes:
        locales = list(LocalComercial.objects.filter(
            cliente=cliente, empresa=empresa
        ).values('id', 'numero'))
        areas = list(AreaComunModel.objects.filter(
            cliente=cliente, empresa=empresa
        ).values('id', 'numero'))
        if locales or areas:
            propiedades_por_cliente[cliente.id] = {
                'locales': locales,
                'areas': areas,
            }

    return render(request, 'cobros_estado_cuenta/revisar.html', {
        'sesion': sesion,
        'movimientos': movimientos,
        'clientes': clientes,
        'tipos_ingreso': tipos_ingreso,
        'facturas_por_cliente_json': json.dumps(facturas_por_cliente),
        'propiedades_por_cliente_json': json.dumps(propiedades_por_cliente),
    })


@login_required
def aplicar_movimiento(request, movimiento_pk):
    movimiento = get_object_or_404(MovimientoEstadoCuenta, pk=movimiento_pk)
    perfil = getattr(request.user, 'perfilusuario', None)
    empresa = perfil.empresa if perfil and not request.user.is_superuser else movimiento.sesion.empresa
    sesion_cuenta = movimiento.sesion.cuenta_bancaria

    if request.method != 'POST':
        return redirect('revisar_sesion_estado_cuenta', pk=movimiento.sesion.pk)

    accion = request.POST.get('accion')
    cliente_id = request.POST.get('cliente_id')
    factura_id = request.POST.get('factura_id')
    tipo_factura = request.POST.get('tipo_factura')  # 'cuota' o 'otros'

    # --- IGNORAR ---
    if accion == 'ignorar':
        movimiento.estado = 'ignorado'
        movimiento.save()
        messages.success(request, "Movimiento ignorado.")

    # --- DEPOSITO NO IDENTIFICADO ---
    elif accion == 'no_identificado':
        pago = Pago.objects.create(
            factura=None,
            fecha_pago=movimiento.fecha,
            monto=movimiento.monto,
            forma_pago='transferencia',
            cuenta_bancaria=sesion_cuenta,
            empresa=empresa,
            registrado_por=request.user,
            identificado=False,
            observaciones=f"Depósito no identificado — {movimiento.descripcion[:100]}",
        )
        movimiento.estado = 'ignorado'
        movimiento.pago_generado = pago
        movimiento.save()
        messages.success(request, f"Registrado como depósito no identificado por ${movimiento.monto:,.2f}.")

    # --- ASIGNAR A FACTURA EXISTENTE ---
    elif accion == 'asignar_factura' and factura_id and tipo_factura:
        from django.db import transaction
        with transaction.atomic():
            if tipo_factura == 'cuota':
                factura = get_object_or_404(Factura, pk=factura_id, empresa=empresa)
                pago = Pago.objects.create(
                    factura=factura,
                    fecha_pago=movimiento.fecha,
                    monto=movimiento.monto,
                    forma_pago='transferencia',
                    cuenta_bancaria=sesion_cuenta,
                    registrado_por=request.user,
                    observaciones=f"Aplicado desde estado de cuenta — {movimiento.descripcion[:80]}",
                )
                factura.actualizar_estatus()
                movimiento.estado = 'asignado_factura'
                movimiento.pago_generado = pago
                movimiento.save()
                messages.success(request, f"Pago de ${movimiento.monto:,.2f} aplicado a factura {factura.folio}.")

            elif tipo_factura == 'otros':
                factura_oi = get_object_or_404(FacturaOtrosIngresos, pk=factura_id, empresa=empresa)
                from facturacion.models import CobroOtrosIngresos
                cobro = CobroOtrosIngresos.objects.create(
                    factura=factura_oi,
                    fecha_cobro=movimiento.fecha,
                    monto=movimiento.monto,
                    forma_cobro='transferencia',
                    cuenta_bancaria=sesion_cuenta,
                    registrado_por=request.user,
                    observaciones=f"Aplicado desde estado de cuenta — {movimiento.descripcion[:80]}",
                )
                factura_oi.actualizar_estatus()
                movimiento.estado = 'asignado_factura'
                movimiento.factura_otros_ingresos = factura_oi
                movimiento.save()
                messages.success(request, f"Cobro de ${movimiento.monto:,.2f} aplicado a {factura_oi.folio}.")

    # --- CREAR FACTURA DE CUOTA NUEVA + PAGO ---
    elif accion == 'crear_factura_cuota' and cliente_id:
        from django.db import transaction, IntegrityError
        import re as re_module
        from facturacion.models import LocalComercial, CobroOtrosIngresos
        from areas.models import AreaComun as AreaComunModel

        cliente = get_object_or_404(Cliente, pk=cliente_id, empresa=empresa)
        tipo_cuota = request.POST.get('tipo_cuota', 'mantenimiento')
        local_id = request.POST.get('local_id')
        area_id = request.POST.get('area_id')
        fecha_vencimiento = request.POST.get('fecha_vencimiento', str(movimiento.fecha))

        local = get_object_or_404(LocalComercial, pk=local_id, empresa=empresa) if local_id else None
        area = get_object_or_404(AreaComunModel, pk=area_id, empresa=empresa) if area_id else None

        prefix = "EDC-L"
        guardado = False
        with transaction.atomic():
            for intento in range(5):
                try:
                    last_folio = (
                        Factura.objects.select_for_update()
                        .filter(empresa=empresa, folio__startswith=prefix)
                        .order_by('-folio').values_list('folio', flat=True).first()
                    )
                    last_num = int(last_folio.replace(prefix, "")) if last_folio and re_module.match(r'^EDC-L\d{5}$', last_folio) else 0
                    folio = f"{prefix}{last_num + 1:05d}"
                    factura_nueva = Factura.objects.create(
                        empresa=empresa, cliente=cliente,
                        local=local, area_comun=area,
                        tipo_cuota=tipo_cuota, folio=folio,
                        fecha_emision=movimiento.fecha,
                        fecha_vencimiento=fecha_vencimiento,
                        monto=movimiento.monto,
                        observaciones=f"Generado desde estado de cuenta — {movimiento.descripcion[:80]}",
                        estatus='pendiente',
                    )
                    pago = Pago.objects.create(
                        factura=factura_nueva,
                        fecha_pago=movimiento.fecha,
                        monto=movimiento.monto,
                        forma_pago='transferencia',
                        cuenta_bancaria=sesion_cuenta,
                        registrado_por=request.user,
                        observaciones="Aplicado automáticamente desde estado de cuenta",
                    )
                    factura_nueva.actualizar_estatus()
                    movimiento.estado = 'asignado_factura'
                    movimiento.pago_generado = pago
                    movimiento.save()
                    guardado = True
                    break
                except IntegrityError:
                    continue
        if guardado:
            messages.success(request, f"Factura {folio} creada y pago aplicado.")
        else:
            messages.error(request, "No se pudo generar el folio. Intenta de nuevo.")

    # --- CREAR FACTURA OTROS INGRESOS NUEVA + COBRO ---
    elif accion == 'crear_factura_otros' and cliente_id:
        from django.db import transaction, IntegrityError
        import re as re_module
        from facturacion.models import CobroOtrosIngresos

        cliente = get_object_or_404(Cliente, pk=cliente_id, empresa=empresa)
        tipo_ingreso_id = request.POST.get('tipo_ingreso_id')
        tipo_ingreso = get_object_or_404(TipoOtroIngreso, pk=tipo_ingreso_id, empresa=empresa) if tipo_ingreso_id else None

        prefix = "EDC-F"
        guardado = False
        with transaction.atomic():
            for intento in range(5):
                try:
                    last_folio = (
                        FacturaOtrosIngresos.objects.select_for_update()
                        .filter(empresa=empresa, folio__startswith=prefix)
                        .order_by('-folio').values_list('folio', flat=True).first()
                    )
                    last_num = int(last_folio.replace(prefix, "")) if last_folio and re_module.match(r'^EDC-F\d{5}$', last_folio) else 0
                    folio = f"{prefix}{last_num + 1:05d}"
                    factura_oi = FacturaOtrosIngresos.objects.create(
                        empresa=empresa, cliente=cliente,
                        tipo_ingreso=tipo_ingreso, folio=folio,
                        fecha_vencimiento=movimiento.fecha,
                        monto=movimiento.monto,
                        observaciones=f"Generado desde estado de cuenta — {movimiento.descripcion[:80]}",
                        estatus='pendiente',
                    )
                    cobro = CobroOtrosIngresos.objects.create(
                        factura=factura_oi,
                        fecha_cobro=movimiento.fecha,
                        monto=movimiento.monto,
                        forma_cobro='transferencia',
                        cuenta_bancaria=sesion_cuenta,
                        registrado_por=request.user,
                        observaciones="Aplicado automáticamente desde estado de cuenta",
                    )
                    factura_oi.actualizar_estatus()
                    movimiento.estado = 'factura_nueva'
                    movimiento.factura_otros_ingresos = factura_oi
                    movimiento.save()
                    guardado = True
                    break
                except IntegrityError:
                    continue
        if guardado:
            messages.success(request, f"Factura {folio} creada y cobro registrado.")
        else:
            messages.error(request, "No se pudo generar el folio. Intenta de nuevo.")

    return redirect('revisar_sesion_estado_cuenta', pk=movimiento.sesion.pk)
