# Create your views here.
import json
#import base64
import os
import threading
import anthropic
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.conf import settings
from .models import AplicacionMovimientoEstadoCuenta, SesionEstadoCuenta, MovimientoEstadoCuenta
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
from facturacion.models import LocalComercial  
from areas.models import AreaComun
from django.core.paginator import Paginator
from collections import defaultdict
from django.db.models import F
from django.db import connection, transaction
from django.db import IntegrityError
import re as re_module





logger = logging.getLogger(__name__)

def procesar_estado_cuenta_en_segundo_plano(sesion_id, archivo_bytes, archivo_nombre):
    """
    Corre en un hilo aparte, sin acceso a `request`.
    Todo el resultado (éxito o error) se guarda en la sesión misma.
    """
    try:
        sesion = SesionEstadoCuenta.objects.get(pk=sesion_id)
        empresa = sesion.empresa

        datos = extraer_movimientos_con_claude(archivo_bytes, archivo_nombre, empresa)

        def parse_fecha(valor):
            if not valor:
                return None
            try:
                return datetime.date.fromisoformat(valor)
            except (ValueError, TypeError):
                return None

        sesion.banco_detectado = datos.get('banco', '')
        sesion.periodo_inicio = parse_fecha(datos.get('periodo_inicio'))
        sesion.periodo_fin = parse_fecha(datos.get('periodo_fin'))
        sesion.saldo_inicial = datos.get('saldo_inicial')
        sesion.saldo_final = datos.get('saldo_final')
        sesion.total_abonos = datos.get('total_abonos')

        # Validar que el período del estado de cuenta sea del año actual
        hoy = datetime.date.today()
        if sesion.periodo_inicio and sesion.periodo_inicio.year < hoy.year:
            sesion.estado = 'error'
            sesion.error_detalle = (
                f"El estado de cuenta corresponde al año {sesion.periodo_inicio.year}. "
                f"Solo se permiten estados de cuenta del año {hoy.year}."
            )
            sesion.save()
            return

        # NUEVO: Validar que no exista ya un estado de cuenta procesado para el mismo período
        if sesion.periodo_inicio and sesion.periodo_fin:
            filtros_duplicado = {
                'empresa': empresa,
                'periodo_inicio': sesion.periodo_inicio,
                'periodo_fin': sesion.periodo_fin,
                'estado__in': ['listo', 'aplicado'],
            }
            if sesion.cuenta_bancaria_id:
                filtros_duplicado['cuenta_bancaria_id'] = sesion.cuenta_bancaria_id

            duplicado = SesionEstadoCuenta.objects.filter(**filtros_duplicado).exclude(pk=sesion.pk).first()

            if duplicado:
                sesion.estado = 'error'
                sesion.error_detalle = (
                    f"Ya existe un estado de cuenta procesado para el período "
                    f"{sesion.periodo_inicio} al {sesion.periodo_fin}"
                    f"{' en esta cuenta bancaria' if sesion.cuenta_bancaria_id else ''}. "
                    f"Revisa la sesión #{duplicado.pk} en la lista de sesiones."
                )
                sesion.save()
                return

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

            # Resolver la propiedad detectada (local o área) contra la BD
            propiedad_tipo_raw = abono.get('propiedad_tipo')
            propiedad_numero = abono.get('propiedad_numero')
            propiedad_local = None
            propiedad_area = None
            propiedad_tipo_final = None

            if cliente and propiedad_tipo_raw and propiedad_numero:
                if propiedad_tipo_raw == 'local':
                    propiedad_local = LocalComercial.objects.filter(
                        cliente=cliente, numero=propiedad_numero, empresa=empresa
                    ).first()
                    if propiedad_local:
                        propiedad_tipo_final = 'local'
                elif propiedad_tipo_raw == 'area':
                    propiedad_area = AreaComun.objects.filter(
                        cliente=cliente, numero=propiedad_numero, empresa=empresa
                    ).first()
                    if propiedad_area:
                        propiedad_tipo_final = 'area'

            MovimientoEstadoCuenta.objects.create(
                sesion=sesion,
                fecha=fecha,
                descripcion=abono.get('descripcion') or '',
                referencia=abono.get('referencia') or '',
                monto=abono.get('monto', 0),
                cliente_detectado=cliente,
                propiedad_tipo=propiedad_tipo_final,
                propiedad_local=propiedad_local,
                propiedad_area=propiedad_area,
                confianza_match=abono.get('confianza_match') or 'ninguna',
                razon_match=abono.get('razon_match') or '',
                estado='pendiente',
            )

    except Exception as e:
        logger.exception(f"Error procesando sesión {sesion_id} en segundo plano")
        try:
            sesion = SesionEstadoCuenta.objects.get(pk=sesion_id)
            sesion.estado = 'error'
            sesion.error_detalle = str(e)
            sesion.save()
        except Exception:
            pass
    finally:
        connection.close()


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


LOTE_TAMANO = 60  # movimientos por lote enviado a Claude, evita truncar la respuesta


def _leer_dataframe_excel_csv(archivo_bytes, filename):
    """Lee el archivo (CSV o Excel) y devuelve un DataFrame de pandas."""
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

    df = df.dropna(how='all')
    if df.empty:
        raise ValueError("El archivo no contiene datos.")
    return df


def extraer_texto_excel_csv(archivo_bytes, filename):
    """Convierte CSV o Excel a texto tipo tabla (se conserva por compatibilidad)."""
    df = _leer_dataframe_excel_csv(archivo_bytes, filename)
    return df.to_csv(index=False)


def _parsear_json_claude(texto):
    """Limpia markdown y repara JSON truncado si es necesario."""
    texto = texto.strip()
    texto = re.sub(r'^```json\s*', '', texto)
    texto = re.sub(r'\s*```$', '', texto)
    try:
        return json.loads(texto)
    except json.JSONDecodeError:
        ultimo_corchete = texto.rfind('},')
        if ultimo_corchete > 0:
            texto_reparado = texto[:ultimo_corchete + 1] + ']}'
            try:
                return json.loads(texto_reparado)
            except json.JSONDecodeError:
                pass
        raise


def _extraer_encabezado_con_claude(client, df):
    """Extrae banco, número de cuenta y saldos usando solo una muestra de filas."""
    muestra = pd.concat([df.head(15), df.tail(15)]).drop_duplicates()
    texto_muestra = muestra.to_csv(index=False)

    prompt = f"""Analiza este fragmento de un estado de cuenta bancario mexicano (formato tabla)
y extrae ÚNICAMENTE los datos generales del encabezado, NO los movimientos individuales.

Devuelve ÚNICAMENTE JSON válido, sin texto adicional:

{{
  "banco": "BBVA|BANORTE|BANAMEX|SANTANDER|BANREGIO|HSBC|otro",
  "numero_cuenta": "número",
  "periodo_inicio": "YYYY-MM-DD",
  "periodo_fin": "YYYY-MM-DD",
  "saldo_inicial": 0.00,
  "saldo_final": 0.00
}}

Reglas:
- El período casi siempre aparece explícito como "Periodo DEL DD/MM/AAAA AL DD/MM/AAAA" o similar. Ese es el que debes usar para periodo_inicio y periodo_fin.
- Si no puedes determinar el banco o número de cuenta, usa "otro" y cadena vacía respectivamente.
- Si no hay columna de saldo identificable, deja saldo_inicial y saldo_final en null.
- Si no encuentras el período explícito, deja periodo_inicio y periodo_fin en null.

Muestra de la tabla (primeras y últimas filas):
{texto_muestra}
"""
    response = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}]
    )
    if not response.content:
        raise ValueError("Claude no devolvió contenido en la respuesta (encabezado).")
    return _parsear_json_claude(response.content[0].text)


def _extraer_abonos_lote_con_claude(client, lote_df, clientes_json, periodo_inicio=None, periodo_fin=None):
    """Extrae los abonos de un fragmento (lote) de la tabla."""
    texto_lote = lote_df.to_csv(index=False)

    if periodo_inicio and periodo_fin:
        contexto_periodo = (
            f"IMPORTANTE — CONTEXTO DE FECHAS: Este estado de cuenta corresponde al período "
            f"{periodo_inicio} al {periodo_fin}. Las fechas de los movimientos individuales casi "
            f"siempre vienen SIN año (ej. \"01/JUN\", \"15/JUL\") — en esos casos, usa el año que "
            f"corresponda según este período (revisa si el mes cae dentro del rango indicado; si el "
            f"período cruza fin de año, usa el año correcto según el mes)."
        )
    else:
        contexto_periodo = (
            "No se pudo determinar el período del estado de cuenta de antemano. Si las fechas de los "
            "movimientos no incluyen año, usa tu mejor criterio basado en el contexto del documento."
        )

    prompt = f"""Analiza este fragmento de un estado de cuenta bancario mexicano (formato tabla)
y extrae SOLO los abonos (depósitos, columna ABONOS con valor positivo).

{contexto_periodo}

Devuelve ÚNICAMENTE JSON válido, sin texto adicional, sin explicaciones:

{{
  "abonos": [
    {{
      "fecha": "YYYY-MM-DD",
      "descripcion": "máximo 80 caracteres",
      "referencia": "referencia corta",
      "monto": 0.00,
      "cliente_id": null,
      "propiedad_tipo": null,
      "propiedad_numero": null,
      "confianza_match": "alta|media|baja|ninguna",
      "razon_match": "máximo 40 caracteres"
    }}
  ]
}}

Clientes de la empresa, con sus propiedades (locales y áreas comunes) para matching:
{clientes_json}

Cada propiedad tiene una referencia de pago única con el formato:
RF-{{cliente_id de 5 dígitos}}-{{L o A}}{{número de local/área saneado}}-{{sufijo aleatorio}}
Ejemplo: RF-00042-LD02-X7K3 → cliente 42, Local D02.

Reglas:
- Incluye SOLO abonos (columna ABONOS con valor positivo)
- confianza "alta": la referencia de pago exacta de alguna propiedad aparece en la descripción.
  En este caso llena "propiedad_tipo" ("local" o "area") y "propiedad_numero"
- confianza "media": el nombre del cliente coincide claramente en la descripción (aunque venga
  abreviado, sin acentos o en otro orden). Si el concepto menciona un local/área que coincide
  con una propiedad del cliente, llena también "propiedad_tipo"/"propiedad_numero"
- confianza "baja": coincidencia parcial débil, o el concepto sugiere el cliente/propiedad sin
  más confirmación
- confianza "ninguna": no se puede identificar
- Normaliza nombres para comparar: ignora acentos, mayúsculas/minúsculas, comas y guiones
- Procesa TODAS las filas de este fragmento, no omitas ninguna

Fragmento de la tabla:
{texto_lote}
"""
    response = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=8000,
        messages=[{"role": "user", "content": prompt}]
    )
    if not response.content:
        raise ValueError("Claude no devolvió contenido en la respuesta (lote de abonos).")
    data = _parsear_json_claude(response.content[0].text)
    return data.get('abonos', [])


def extraer_movimientos_con_claude(archivo_bytes, filename, empresa):
    """Llama a Claude API para extraer los movimientos del archivo (CSV o Excel), en lotes."""
    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

    from locales.models import LocalComercial
    from areas.models import AreaComun

    clientes_qs = Cliente.objects.filter(empresa=empresa, activo=True)
    clientes_data = []
    for cliente in clientes_qs:
        propiedades = []
        for local in LocalComercial.objects.filter(cliente=cliente, activo=True):
            if local.referencia_pago:
                propiedades.append({
                    'tipo': 'local', 'numero': local.numero, 'referencia_pago': local.referencia_pago,
                })
        for area in AreaComun.objects.filter(cliente=cliente, activo=True):
            if area.referencia_pago:
                propiedades.append({
                    'tipo': 'area', 'numero': area.numero, 'referencia_pago': area.referencia_pago,
                })
        clientes_data.append({
            'id': cliente.id, 'nombre': cliente.nombre, 'rfc': cliente.rfc, 'propiedades': propiedades,
        })
    clientes_json = json.dumps(clientes_data, ensure_ascii=False)

    extension = filename.lower().rsplit('.', 1)[-1] if '.' in filename else ''
    if extension not in ('csv', 'xls', 'xlsx'):
        raise ValueError(f"Tipo de archivo no soportado: .{extension}. Solo se aceptan CSV o Excel.")

    df = _leer_dataframe_excel_csv(archivo_bytes, filename)

    # 1) Encabezado (banco, cuenta, saldos, período) — solo con una muestra de filas
    encabezado = _extraer_encabezado_con_claude(client, df)
    periodo_inicio_hdr = encabezado.get('periodo_inicio')
    periodo_fin_hdr = encabezado.get('periodo_fin')

    # 2) Abonos, en lotes, pasando el período conocido para resolver fechas sin año
    abonos_totales = []
    for i in range(0, len(df), LOTE_TAMANO):
        lote_df = df.iloc[i:i + LOTE_TAMANO]
        abonos_lote = _extraer_abonos_lote_con_claude(
            client, lote_df, clientes_json,
            periodo_inicio=periodo_inicio_hdr, periodo_fin=periodo_fin_hdr
        )
        abonos_totales.extend(abonos_lote)

    # 3) Período final: preferir el del encabezado (explícito, con año); si no vino, calcular de los abonos
    if periodo_inicio_hdr and periodo_fin_hdr:
        periodo_inicio = periodo_inicio_hdr
        periodo_fin = periodo_fin_hdr
    else:
        fechas_validas = []
        for a in abonos_totales:
            try:
                fechas_validas.append(datetime.date.fromisoformat(a.get('fecha')))
            except Exception:
                pass
        periodo_inicio = min(fechas_validas).isoformat() if fechas_validas else None
        periodo_fin = max(fechas_validas).isoformat() if fechas_validas else None

    total_abonos = sum(float(a.get('monto') or 0) for a in abonos_totales)

    return {
        'banco': encabezado.get('banco', ''),
        'numero_cuenta': encabezado.get('numero_cuenta', ''),
        'periodo_inicio': periodo_inicio,
        'periodo_fin': periodo_fin,
        'saldo_inicial': encabezado.get('saldo_inicial'),
        'saldo_final': encabezado.get('saldo_final'),
        'total_abonos': total_abonos,
        'abonos': abonos_totales,
    }


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
        archivo_bytes = archivo.read()
        archivo.seek(0)  # Reposicionar para que Django pueda guardarlo correctamente

        # Crear la sesión
        sesion = SesionEstadoCuenta.objects.create(
            empresa=empresa,
            cuenta_bancaria=cuenta,
            archivo=archivo,
            estado='procesando',
            registrado_por=request.user,
        )

        # Procesar en segundo plano — la vista responde de inmediato
        hilo = threading.Thread(
            target=procesar_estado_cuenta_en_segundo_plano,
            args=(sesion.id, archivo_bytes, archivo.name),
            daemon=True,
        )
        hilo.start()

        return redirect('procesando_sesion_estado_cuenta', pk=sesion.pk)

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

    # Filtro por estado (server-side ahora, ya no solo JS)
    filtro = request.GET.get('estado', 'todos')
    movimientos_qs = sesion.movimientos.select_related(
        'cliente_detectado', 'propiedad_local', 'propiedad_area'
    ).all()

    if filtro == 'pendiente':
        movimientos_qs = movimientos_qs.filter(estado__in=['pendiente', 'parcial'])

    elif filtro == 'aplicado':
        movimientos_qs = movimientos_qs.filter(estado__in=['asignado_factura', 'factura_nueva'])
    elif filtro == 'ignorado':
        movimientos_qs = movimientos_qs.filter(estado='ignorado')
    # 'todos' no filtra

    # Conteos para los botones (sobre el total de la sesión, no del filtro actual)
    conteos = {
        'todos': sesion.movimientos.count(),
        'pendiente': sesion.movimientos.filter(estado__in=['pendiente', 'parcial']).count(),
        'aplicado': sesion.movimientos.filter(estado__in=['asignado_factura', 'factura_nueva']).count(),
        'ignorado': sesion.movimientos.filter(estado='ignorado').count(),
    }

    paginator = Paginator(movimientos_qs, 20)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)


    #movimientos = sesion.movimientos.all()
    clientes = Cliente.objects.filter(empresa=empresa, activo=True)
    tipos_ingreso = TipoOtroIngreso.objects.filter(empresa=empresa)

     # --- Facturas por cliente: 2 consultas totales en vez de 2 por cliente ---
    facturas_por_cliente = defaultdict(list)

    facturas_cuota = (
        Factura.objects.filter(empresa=empresa, estatus='pendiente', activo=True, cliente__in=clientes)
        .select_related('local', 'area_comun')
        .order_by('-fecha_vencimiento')
    )
    for f in facturas_cuota:
        facturas_por_cliente[f.cliente_id].append({
            'id': f.id, 'tipo': 'cuota', 'folio': f.folio,
            'concepto': f.get_tipo_cuota_display(), 'monto': float(f.saldo_pendiente),
            'vencimiento': str(f.fecha_vencimiento),
            'local': f.local.numero if f.local else None,
            'area': f.area_comun.numero if f.area_comun else None,
        })

    facturas_otros = (
        FacturaOtrosIngresos.objects.filter(empresa=empresa, estatus='pendiente', activo=True, cliente__in=clientes)
        .select_related('tipo_ingreso')
        .order_by('-fecha_vencimiento')
    )
    for f in facturas_otros:
        facturas_por_cliente[f.cliente_id].append({
            'id': f.id, 'tipo': 'otros',
            'folio': f.folio, 'concepto': f.tipo_ingreso.nombre if f.tipo_ingreso else 'Otro ingreso',
            'monto': float(f.saldo), 'vencimiento': str(f.fecha_vencimiento),
            'local': None, 'area': None,
        })

    # Límite de 10 por cliente, igual que antes, ya en memoria (sin consultas extra)
    facturas_por_cliente = {
        cid: sorted(lista, key=lambda x: x['vencimiento'], reverse=True)[:10]
        for cid, lista in facturas_por_cliente.items()
    }

    # --- Propiedades por cliente: 2 consultas totales en vez de 2 por cliente ---
    propiedades_por_cliente = defaultdict(lambda: {'locales': [], 'areas': []})

    for local in LocalComercial.objects.filter(cliente__in=clientes, empresa=empresa).values('id', 'numero', 'cliente_id'):
        propiedades_por_cliente[local['cliente_id']]['locales'].append({'id': local['id'], 'numero': local['numero']})

    for area in AreaComun.objects.filter(cliente__in=clientes, empresa=empresa).values('id', 'numero', 'cliente_id'):
        propiedades_por_cliente[area['cliente_id']]['areas'].append({'id': area['id'], 'numero': area['numero']})

    propiedades_por_cliente = dict(propiedades_por_cliente)

    return render(request, 'cobros_estado_cuenta/revisar.html', {
        'sesion': sesion,
        'movimientos': page_obj,
        'page_obj': page_obj,
        'filtro_actual': filtro,
        'conteos': conteos,
        'clientes': clientes,
        'tipos_ingreso': tipos_ingreso,
        'facturas_por_cliente_json': json.dumps(facturas_por_cliente),
        'propiedades_por_cliente_json': json.dumps(propiedades_por_cliente),
    })

@login_required
def ver_procesando_sesion(request, pk):
    perfil = getattr(request.user, 'perfilusuario', None)
    if request.user.is_superuser:
        sesion = get_object_or_404(SesionEstadoCuenta, pk=pk)
    else:
        empresa = perfil.empresa if perfil else None
        sesion = get_object_or_404(SesionEstadoCuenta, pk=pk, empresa=empresa)

    if sesion.estado == 'listo':
        return redirect('revisar_sesion_estado_cuenta', pk=sesion.pk)
    if sesion.estado == 'error':
        messages.error(request, sesion.error_detalle or "Ocurrió un error al procesar el archivo.")
        return redirect('lista_sesiones_estado_cuenta')

    return render(request, 'cobros_estado_cuenta/procesando.html', {'sesion': sesion})


@login_required
def estado_sesion_json(request, pk):
    from django.http import JsonResponse
    from django.urls import reverse

    perfil = getattr(request.user, 'perfilusuario', None)
    if request.user.is_superuser:
        sesion = get_object_or_404(SesionEstadoCuenta, pk=pk)
    else:
        empresa = perfil.empresa if perfil else None
        sesion = get_object_or_404(SesionEstadoCuenta, pk=pk, empresa=empresa)

    data = {'estado': sesion.estado}
    if sesion.estado == 'listo':
        data['redirect_url'] = reverse('revisar_sesion_estado_cuenta', args=[sesion.pk])
    elif sesion.estado == 'error':
        data['error'] = sesion.error_detalle or "Ocurrió un error al procesar el archivo."
    return JsonResponse(data)


####funcion para aplicar un movimiento a una factura o crear una nueva

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
    tipo_factura = request.POST.get('tipo_factura')

    # --- IGNORAR (cierra el movimiento, aplicado o no, sin repartir más) ---
    if accion == 'ignorar':
        movimiento.estado = 'ignorado'
        movimiento.save()
        messages.success(request, "Movimiento ignorado.")
        return redirect('revisar_sesion_estado_cuenta', pk=movimiento.sesion.pk)

    # A partir de aquí, todas las acciones necesitan saldo disponible
    if movimiento.saldo_restante <= 0:
        messages.error(request, "Este movimiento ya no tiene saldo disponible para asignar.")
        return redirect('revisar_sesion_estado_cuenta', pk=movimiento.sesion.pk)

    # --- Validar que el cliente elegido coincida con el ya confirmado (si hay saldo parcial) ---
    def validar_cliente_bloqueado(cliente):
        if movimiento.cliente_asignado_id and cliente.id != movimiento.cliente_asignado_id:
            return False
        return True

    # --- DEPOSITO NO IDENTIFICADO (usa el saldo restante, no el monto original) ---
    if accion == 'no_identificado':
        monto_a_usar = movimiento.saldo_restante
        pago = Pago.objects.create(
            factura=None,
            fecha_pago=movimiento.fecha,
            monto=monto_a_usar,
            forma_pago='transferencia',
            cuenta_bancaria=sesion_cuenta,
            empresa=empresa,
            registrado_por=request.user,
            identificado=False,
            observaciones=f"Depósito no identificado — {movimiento.descripcion[:100]}",
        )
        AplicacionMovimientoEstadoCuenta.objects.create(
            movimiento=movimiento, monto=monto_a_usar, pago=pago,
        )
        movimiento.monto_aplicado = F('monto_aplicado') + monto_a_usar
        movimiento.estado = 'ignorado'  # se cierra, ya no admite más asignaciones
        movimiento.pago_generado = pago
        movimiento.save()
        messages.success(request, f"Registrado como depósito no identificado por ${monto_a_usar:,.2f}.")

    # --- ASIGNAR A FACTURA EXISTENTE (usa min(saldo factura, saldo restante movimiento)) ---
    elif accion == 'asignar_factura' and factura_id and tipo_factura and cliente_id:
        cliente = get_object_or_404(Cliente, pk=cliente_id, empresa=empresa)

        if not validar_cliente_bloqueado(cliente):
            cliente_bloqueado = movimiento.cliente_asignado
            messages.error(
                request,
                f"Este movimiento ya tiene saldo asignado al cliente '{cliente_bloqueado.nombre}'. "
                f"El resto del saldo solo puede aplicarse a facturas de ese mismo cliente."
            )
            return redirect('revisar_sesion_estado_cuenta', pk=movimiento.sesion.pk)

        with transaction.atomic():
            if tipo_factura == 'cuota':
                factura = get_object_or_404(Factura, pk=factura_id, empresa=empresa)
                monto_a_aplicar = min(factura.saldo_pendiente, movimiento.saldo_restante)

                if monto_a_aplicar <= 0:
                    messages.error(request, "Esa factura ya no tiene saldo pendiente.")
                    return redirect('revisar_sesion_estado_cuenta', pk=movimiento.sesion.pk)

                pago = Pago.objects.create(
                    factura=factura,
                    fecha_pago=movimiento.fecha,
                    monto=monto_a_aplicar,
                    forma_pago='transferencia',
                    cuenta_bancaria=sesion_cuenta,
                    registrado_por=request.user,
                    observaciones=f"Aplicado desde estado de cuenta — {movimiento.descripcion[:80]}",
                )
                factura.actualizar_estatus()

                AplicacionMovimientoEstadoCuenta.objects.create(
                    movimiento=movimiento, monto=monto_a_aplicar, pago=pago, factura_cuota=factura,
                )

                movimiento.cliente_asignado = movimiento.cliente_asignado or cliente
                movimiento.pago_generado = pago
                movimiento.monto_aplicado = F('monto_aplicado') + monto_a_aplicar
                movimiento.save()
                movimiento.refresh_from_db()

                if movimiento.saldo_restante <= 0:
                    movimiento.estado = 'asignado_factura'
                    mensaje_extra = "Movimiento completamente asignado."
                else:
                    movimiento.estado = 'parcial'
                    mensaje_extra = f"Quedan ${movimiento.saldo_restante:,.2f} disponibles de este movimiento para asignar a otra factura de {cliente.nombre}."
                movimiento.save()

                messages.success(
                    request,
                    f"Pago de ${monto_a_aplicar:,.2f} aplicado a factura {factura.folio}. {mensaje_extra}"
                )

            elif tipo_factura == 'otros':
                from facturacion.models import CobroOtrosIngresos
                factura_oi = get_object_or_404(FacturaOtrosIngresos, pk=factura_id, empresa=empresa)
                monto_a_aplicar = min(factura_oi.saldo, movimiento.saldo_restante)

                if monto_a_aplicar <= 0:
                    messages.error(request, "Esa factura ya no tiene saldo pendiente.")
                    return redirect('revisar_sesion_estado_cuenta', pk=movimiento.sesion.pk)

                cobro = CobroOtrosIngresos.objects.create(
                    factura=factura_oi,
                    fecha_cobro=movimiento.fecha,
                    monto=monto_a_aplicar,
                    forma_cobro='transferencia',
                    cuenta_bancaria=sesion_cuenta,
                    registrado_por=request.user,
                    observaciones=f"Aplicado desde estado de cuenta — {movimiento.descripcion[:80]}",
                )
                factura_oi.actualizar_estatus()

                AplicacionMovimientoEstadoCuenta.objects.create(
                    movimiento=movimiento, monto=monto_a_aplicar,
                    cobro_otros_ingresos=cobro, factura_otros=factura_oi,
                )

                movimiento.cliente_asignado = movimiento.cliente_asignado or cliente
                movimiento.factura_otros_ingresos = factura_oi
                movimiento.monto_aplicado = F('monto_aplicado') + monto_a_aplicar
                movimiento.save()
                movimiento.refresh_from_db()

                if movimiento.saldo_restante <= 0:
                    movimiento.estado = 'asignado_factura'
                    mensaje_extra = "Movimiento completamente asignado."
                else:
                    movimiento.estado = 'parcial'
                    mensaje_extra = f"Quedan ${movimiento.saldo_restante:,.2f} disponibles de este movimiento para asignar a otra factura de {cliente.nombre}."
                movimiento.save()

                messages.success(
                    request,
                    f"Cobro de ${monto_a_aplicar:,.2f} aplicado a {factura_oi.folio}. {mensaje_extra}"
                )

    # --- CREAR FACTURA DE CUOTA NUEVA + PAGO (usa el saldo restante del movimiento) ---
    elif accion == 'crear_factura_cuota' and cliente_id:
       

        cliente = get_object_or_404(Cliente, pk=cliente_id, empresa=empresa)

        if not validar_cliente_bloqueado(cliente):
            cliente_bloqueado = movimiento.cliente_asignado
            messages.error(
                request,
                f"Este movimiento ya tiene saldo asignado al cliente '{cliente_bloqueado.nombre}'."
            )
            return redirect('revisar_sesion_estado_cuenta', pk=movimiento.sesion.pk)

        tipo_cuota = request.POST.get('tipo_cuota', 'mantenimiento')
        local_id = request.POST.get('local_id')
        area_id = request.POST.get('area_id')
        fecha_vencimiento = request.POST.get('fecha_vencimiento', str(movimiento.fecha))

        local = get_object_or_404(LocalComercial, pk=local_id, empresa=empresa) if local_id else None
        area = get_object_or_404(AreaComun, pk=area_id, empresa=empresa) if area_id else None

        monto_a_usar = movimiento.saldo_restante
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
                        monto=monto_a_usar,
                        observaciones=f"Generado desde estado de cuenta — {movimiento.descripcion[:80]}",
                        estatus='pendiente',
                    )
                    pago = Pago.objects.create(
                        factura=factura_nueva,
                        fecha_pago=movimiento.fecha,
                        monto=monto_a_usar,
                        forma_pago='transferencia',
                        cuenta_bancaria=sesion_cuenta,
                        registrado_por=request.user,
                        observaciones="Aplicado automáticamente desde estado de cuenta",
                    )
                    factura_nueva.actualizar_estatus()

                    AplicacionMovimientoEstadoCuenta.objects.create(
                        movimiento=movimiento, monto=monto_a_usar, pago=pago, factura_cuota=factura_nueva,
                    )

                    movimiento.cliente_asignado = movimiento.cliente_asignado or cliente
                    movimiento.pago_generado = pago
                    movimiento.monto_aplicado = F('monto_aplicado') + monto_a_usar
                    movimiento.estado = 'asignado_factura'  # se consume todo el saldo restante
                    movimiento.save()
                    guardado = True
                    break
                except IntegrityError:
                    continue
        if guardado:
            messages.success(request, f"Factura {folio} creada y pago de ${monto_a_usar:,.2f} aplicado.")
        else:
            messages.error(request, "No se pudo generar el folio. Intenta de nuevo.")

    # --- CREAR FACTURA OTROS INGRESOS NUEVA + COBRO (usa el saldo restante del movimiento) ---
    elif accion == 'crear_factura_otros' and cliente_id:
        
        cliente = get_object_or_404(Cliente, pk=cliente_id, empresa=empresa)

        if not validar_cliente_bloqueado(cliente):
            cliente_bloqueado = movimiento.cliente_asignado
            messages.error(
                request,
                f"Este movimiento ya tiene saldo asignado al cliente '{cliente_bloqueado.nombre}'."
            )
            return redirect('revisar_sesion_estado_cuenta', pk=movimiento.sesion.pk)

        tipo_ingreso_id = request.POST.get('tipo_ingreso_id')
        tipo_ingreso = get_object_or_404(TipoOtroIngreso, pk=tipo_ingreso_id, empresa=empresa) if tipo_ingreso_id else None

        monto_a_usar = movimiento.saldo_restante
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
                        monto=monto_a_usar,
                        observaciones=f"Generado desde estado de cuenta — {movimiento.descripcion[:80]}",
                        estatus='pendiente',
                    )
                    cobro = CobroOtrosIngresos.objects.create(
                        factura=factura_oi,
                        fecha_cobro=movimiento.fecha,
                        monto=monto_a_usar,
                        forma_cobro='transferencia',
                        cuenta_bancaria=sesion_cuenta,
                        registrado_por=request.user,
                        observaciones="Aplicado automáticamente desde estado de cuenta",
                    )
                    factura_oi.actualizar_estatus()

                    AplicacionMovimientoEstadoCuenta.objects.create(
                        movimiento=movimiento, monto=monto_a_usar,
                        cobro_otros_ingresos=cobro, factura_otros=factura_oi,
                    )

                    movimiento.cliente_asignado = movimiento.cliente_asignado or cliente
                    movimiento.factura_otros_ingresos = factura_oi
                    movimiento.monto_aplicado = F('monto_aplicado') + monto_a_usar
                    movimiento.estado = 'factura_nueva'
                    movimiento.save()
                    guardado = True
                    break
                except IntegrityError:
                    continue
        if guardado:
            messages.success(request, f"Factura {folio} creada y cobro de ${monto_a_usar:,.2f} registrado.")
        else:
            messages.error(request, "No se pudo generar el folio. Intenta de nuevo.")

    return redirect('revisar_sesion_estado_cuenta', pk=movimiento.sesion.pk)