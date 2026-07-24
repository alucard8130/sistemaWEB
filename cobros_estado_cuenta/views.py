# Create your views here.
import json
#import base64
import os
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
#import pdfplumber
import io
import logging
import pandas as pd
from adobe.pdfservices.operation.auth.service_principal_credentials import ServicePrincipalCredentials
from adobe.pdfservices.operation.exception.exceptions import ServiceApiException, ServiceUsageException, SdkException
from adobe.pdfservices.operation.pdf_services import PDFServices
from adobe.pdfservices.operation.pdf_services_media_type import PDFServicesMediaType
from adobe.pdfservices.operation.pdfjobs.jobs.export_pdf_job import ExportPDFJob
from adobe.pdfservices.operation.pdfjobs.params.export_pdf.export_pdf_params import ExportPDFParams
from adobe.pdfservices.operation.pdfjobs.params.export_pdf.export_pdf_target_format import ExportPDFTargetFormat
from adobe.pdfservices.operation.pdfjobs.result.export_pdf_result import ExportPDFResult
from django.http import HttpResponse

logger = logging.getLogger(__name__)


def extraer_texto_excel_csv(archivo_bytes, filename):
    """Convierte CSV o Excel a texto tipo tabla para mandar a Claude."""
    filename_lower = filename.lower()

    try:
        if filename_lower.endswith('.csv'):
            df = None
            ultimo_error = None
            for encoding in ('utf-8', 'latin-1', 'cp1252'):
                try:
                    df = pd.read_csv(io.BytesIO(archivo_bytes), encoding=encoding, sep=None, engine='python')
                    break
                except Exception as e:
                    ultimo_error = e
                    continue
            if df is None:
                raise ValueError(f"No se pudo leer el CSV: {ultimo_error}")
        else:
            df = pd.read_excel(io.BytesIO(archivo_bytes))
    except Exception as e:
        raise ValueError(f"No se pudo leer el archivo: {e}")

    df = df.dropna(how='all')  # quitar filas completamente vacías

    if df.empty:
        raise ValueError("El archivo no contiene datos.")

    return df.to_csv(index=False)


def convertir_pdf_a_excel_adobe(pdf_bytes):
    """
    Convierte un PDF a Excel usando Adobe PDF Services API.
    Retorna los bytes del .xlsx resultante. Lanza excepción si falla.
    """
    client_id = os.environ.get('ADOBE_CLIENT_ID')
    client_secret = os.environ.get('ADOBE_CLIENT_SECRET')

    if not client_id or not client_secret:
        raise ValueError("Credenciales de Adobe (ADOBE_CLIENT_ID / ADOBE_CLIENT_SECRET) no configuradas.")

    credentials = ServicePrincipalCredentials(
        client_id=client_id,
        client_secret=client_secret
    )
    pdf_services = PDFServices(credentials=credentials)

    input_asset = pdf_services.upload(
        input_stream=pdf_bytes,
        mime_type=PDFServicesMediaType.PDF
    )

    export_pdf_params = ExportPDFParams(target_format=ExportPDFTargetFormat.XLSX)
    export_pdf_job = ExportPDFJob(input_asset=input_asset, export_pdf_params=export_pdf_params)

    location = pdf_services.submit(export_pdf_job)
    pdf_services_response = pdf_services.get_job_result(location, ExportPDFResult)

    result_asset = pdf_services_response.get_result().get_asset()
    stream_asset = pdf_services.get_content(result_asset)

    return stream_asset.get_input_stream()

@login_required
def convertir_pdf_preview(request):
    """
    Convierte un PDF a Excel usando Adobe y lo devuelve para descarga,
    sin tocar la base de datos ni llamar a la IA. El usuario revisa/edita
    el Excel y luego lo sube por separado al flujo normal.
    """
    if request.method != 'POST':
        return redirect('subir_estado_cuenta')

    archivo = request.FILES.get('archivo')

    if not archivo:
        messages.error(request, "Debes subir un archivo PDF.")
        return redirect('subir_estado_cuenta')

    if not archivo.name.lower().endswith('.pdf'):
        messages.error(request, "Solo se puede convertir un archivo PDF.")
        return redirect('subir_estado_cuenta')

    pdf_bytes = archivo.read()

    try:
        excel_bytes = convertir_pdf_a_excel_adobe(pdf_bytes)
    except (ServiceApiException, ServiceUsageException, SdkException, ValueError) as e:
        logger.error(f"Error al convertir PDF a Excel (preview): {e}")
        messages.error(request, f"No se pudo convertir el archivo: {e}")
        return redirect('subir_estado_cuenta')

    nombre_salida = archivo.name.rsplit('.', 1)[0] + '_convertido.xlsx'

    response = HttpResponse(
        excel_bytes,
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="{nombre_salida}"'
    return response


def extraer_movimientos_con_claude(archivo_bytes, filename, empresa):
    """Llama a Claude API para extraer los movimientos del archivo (CSV o Excel)"""
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

    extension = filename.lower().rsplit('.', 1)[-1] if '.' in filename else ''

    if extension not in ('csv', 'xls', 'xlsx'):
        raise ValueError(f"Tipo de archivo no soportado: .{extension}. Solo se aceptan CSV o Excel.")

    texto_tabla = extraer_texto_excel_csv(archivo_bytes, filename)
    contenido = [
        {"type": "text", "text": f"Estado de cuenta (datos en formato CSV):\n\n{texto_tabla}"},
        {"type": "text", "text": prompt}
    ]

    response = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=16000,
        messages=[{"role": "user", "content": contenido}]
    )

    if not response.content:
        raise ValueError("Claude no devolvió contenido en la respuesta.")

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
def subir_estado_cuenta(request):
    perfil = getattr(request.user, 'perfilusuario', None)
    empresa = perfil.empresa if perfil and not request.user.is_superuser else None

    cuentas = CuentaBancaria.objects.filter(empresa=empresa, activa=True) if empresa else CuentaBancaria.objects.none()

    if request.method == 'POST':
        archivo = request.FILES.get('archivo')
        cuenta_id = request.POST.get('cuenta_bancaria_id')

        if not archivo:
            messages.error(request, "Debes subir un archivo PDF, CSV o Excel.")
            return render(request, 'cobros_estado_cuenta/subir.html', {'cuentas': cuentas})

        if archivo.name.lower().endswith('.pdf'):
            messages.error(
                request,
                "Los archivos PDF deben convertirse a Excel primero. "
                "Usa la opción 'Convertir a Excel y descargar' arriba, revisa el archivo, y luego súbelo aquí."
            )
            return render(request, 'cobros_estado_cuenta/subir.html', {'cuentas': cuentas})

        extensiones_validas = ('.csv', '.xls', '.xlsx')

        if not archivo.name.lower().endswith(extensiones_validas):
            messages.error(request, "Solo se aceptan archivos CSV o Excel (.xls, .xlsx).")
            return render(request, 'cobros_estado_cuenta/subir.html', {'cuentas': cuentas})

        cuenta = None
        if cuenta_id:
            cuenta = get_object_or_404(CuentaBancaria, pk=cuenta_id, empresa=empresa)

        # ← Leer bytes ANTES de crear la sesión (antes de que Django mueva el archivo)
        archivo_bytes  = archivo.read()
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
            datos = extraer_movimientos_con_claude(archivo_bytes, archivo.name, empresa)
            # Convertir fechas del encabezado (vienen como string del JSON de Claude)
            def parse_fecha(valor):
                if not valor:
                    return None
                try:
                    return datetime.date.fromisoformat(valor)
                except (ValueError, TypeError):
                    return None
                
            # Actualizar la sesión con los datos del encabezado
            sesion.banco_detectado = datos.get('banco', '')
            sesion.periodo_inicio = parse_fecha(datos.get('periodo_inicio'))
            sesion.periodo_fin = parse_fecha(datos.get('periodo_fin'))
            sesion.saldo_inicial = datos.get('saldo_inicial')
            sesion.saldo_final = datos.get('saldo_final')
            sesion.total_abonos = datos.get('total_abonos')
            sesion.estado = 'listo'
            sesion.save()

            # Validar que el período del estado de cuenta sea del año actual
            hoy = datetime.date.today()
            if sesion.periodo_inicio and sesion.periodo_inicio.year < hoy.year:
                sesion.delete()
                messages.error(request,
                    f"El estado de cuenta corresponde al año {sesion.periodo_inicio.year}. "
                    f"Solo se permiten estados de cuenta del año {hoy.year}."
                )
                return render(request, 'cobros_estado_cuenta/subir.html', {'cuentas': cuentas})

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
                    descripcion=abono.get('descripcion') or '',
                    referencia=abono.get('referencia') or '',
                    monto=abono.get('monto', 0),
                    cliente_detectado=cliente,
                    confianza_match=abono.get('confianza_match') or 'ninguna',
                    razon_match=abono.get('razon_match') or '',
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


###Configuración de vistas para la lista de sesiones y revisión de movimientos
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
    perfil = getattr(request.user, 'perfilusuario', None)
    if request.user.is_superuser:
        sesion = get_object_or_404(SesionEstadoCuenta, pk=pk)
    else:
        empresa = perfil.empresa if perfil else None
        sesion = get_object_or_404(SesionEstadoCuenta, pk=pk, empresa=empresa)

    if request.method == 'POST':
        sesion.delete()
        messages.success(request, "Estado de cuenta eliminado correctamente.")
        return redirect('lista_sesiones_estado_cuenta')
    return render(request, 'cobros_estado_cuenta/eliminar_sesion.html', {'sesion': sesion})


@login_required
def revisar_sesion(request, pk):
    perfil = getattr(request.user, 'perfilusuario', None)
    if request.user.is_superuser:
        sesion = get_object_or_404(SesionEstadoCuenta, pk=pk)
    else:
        empresa_perfil = perfil.empresa if perfil else None
        sesion = get_object_or_404(SesionEstadoCuenta, pk=pk, empresa=empresa_perfil)
        
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
    perfil = getattr(request.user, 'perfilusuario', None)
    if request.user.is_superuser:
        movimiento = get_object_or_404(MovimientoEstadoCuenta, pk=movimiento_pk)
    else:
        empresa_perfil = perfil.empresa if perfil else None
        movimiento = get_object_or_404(MovimientoEstadoCuenta, pk=movimiento_pk, sesion__empresa=empresa_perfil)

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
