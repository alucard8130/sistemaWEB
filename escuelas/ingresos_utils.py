"""Utilidades para el reporte 'Detalle de Pagos' de Academic+ (IPC, Cafeteria,
Colegiaturas) -- parseo, normalizacion de conceptos y formas de pago, y
alta de ingresos con su destino (banco al 100% / fondeo de caja chica)."""

import calendar
import datetime
import hashlib
import re
import unicodedata
from collections import Counter, OrderedDict, defaultdict
from decimal import Decimal, InvalidOperation

import xlrd

CERO = Decimal('0.00')

# ----------------------------------------------------------------------------
# Texto
# ----------------------------------------------------------------------------
def norm(texto):
    """MAYUSCULAS sin acentos ni espacios dobles."""
    t = unicodedata.normalize('NFKD', str(texto or ''))
    t = ''.join(c for c in t if not unicodedata.combining(c))
    return re.sub(r'\s+', ' ', t).strip().upper()


def _dec(valor):
    try:
        return Decimal(str(round(float(valor), 2))).quantize(Decimal('0.01'))
    except (InvalidOperation, TypeError, ValueError):
        return None


def _texto_id(valor):
    """Recibos/matriculas: '026271', 396.0 -> '396'."""
    if valor in ('', None):
        return ''
    if isinstance(valor, float):
        return str(int(valor)) if valor == int(valor) else str(valor)
    return str(valor).strip()


# ----------------------------------------------------------------------------
# Forma de pago
# ----------------------------------------------------------------------------
def _es_amex(n):
    """AMEX / AMERICAN EXPRESS, sin confundir con el banco BANAMEX."""
    return bool(re.search(r'(^|[^A-Z])AMEX|AMERICAN', n))


def es_efectivo(forma_pago):
    return 'EFECTIVO' in norm(forma_pago)


def etiqueta_forma_pago(forma_pago):
    """Unifica 'TARJETA DE CREDITO' / 'TARJETA DE CRÉDITO' etc. en una sola
    etiqueta legible. Distingue terminal (TPV) de portal web."""
    n = norm(forma_pago)
    if not n:
        return 'Sin forma de pago'
    web = ' (portal web)' if 'WEB' in n else ' (terminal)'
    if 'EFECTIVO' in n:
        return 'Efectivo'
    if 'TRANSFER' in n:
        return 'Transferencia'
    if _es_amex(n):
        return 'Tarjeta AMEX' + web
    if 'CREDITO' in n:
        return 'Tarjeta de crédito' + web
    if 'DEBITO' in n:
        return 'Tarjeta de débito' + web
    if 'CHEQUE' in n:
        return 'Cheque'
    if 'DEPOSITO' in n:
        return 'Depósito'
    return str(forma_pago).strip().title()


# Comisiones de referencia del portal web (la comision NO se descuenta del
# ingreso: el usuario la registra como gasto).
COMISION_REFERENCIA = {
    'debito': Decimal('2.12'),
    'credito': Decimal('1.64'),
    'amex': Decimal('2.17'),
}


def tipo_tarjeta_merchant(merchant_id):
    """VISA_DÉBITO_BANCOMER -> 'debito', MASTERCARD_CRÉDITO_. -> 'credito',
    AMEX... -> 'amex'. None si no se reconoce."""
    n = norm(merchant_id)
    if _es_amex(n):
        return 'amex'
    if 'CREDITO' in n:
        return 'credito'
    if 'DEBITO' in n:
        return 'debito'
    return None


# ----------------------------------------------------------------------------
# Categoria / rubro
# ----------------------------------------------------------------------------
def categoria_desde_concepto(concepto):
    c = norm(concepto)
    if c.startswith('COLEGIATURA'):
        return 'colegiatura'
    if c.startswith('INSCRIP'):
        return 'inscripcion'
    return 'otro'


# (palabra clave contenida en el concepto normalizado, rubro). Orden = prioridad.
_REGLAS_RUBRO = [
    ('COLEGIATURA ANUAL', 'Colegiatura anual'),
    ('COLEGIATURA', 'Colegiatura'),
    ('COMEDOR', 'Cafetería'),
    ('POSTRE', 'Cafetería'),
    ('COMIDA', 'Cafetería'),
    ('NATACION', 'Natación'),            # club, seguro, certificado medico, insc natacion
    ('INSCRIP', 'Inscripción'),
    ('GASTOS ADMIN', 'Gastos administrativos'),
    ('SEGURO ESCOLAR', 'Seguro escolar'),
    ('TRANSPORTE', 'Transporte'),
    ('TALLER', 'Talleres'),
    ('CLUB', 'Clubes'),
    ('CURSO', 'Cursos'),
    ('CERTIFIC', 'Certificaciones'),
    ('LIBRO', 'Libros'),
    ('ESTANCIA', 'Estancia'),
    ('PANT', 'Uniformes'),
    ('SUETER', 'Uniformes'),
    ('PLAYERA', 'Uniformes'),
    ('CHAMARRA', 'Uniformes'),
    ('UNIFORME', 'Uniformes'),
    ('SHORT', 'Uniformes'),
    ('MANDIL', 'Uniformes'),
]
RUBRO_SIN_CLASIFICAR = 'Sin clasificar'


def normalizar_rubro(concepto):
    c = norm(concepto)
    for clave, rubro in _REGLAS_RUBRO:
        if clave in c:
            return rubro
    return RUBRO_SIN_CLASIFICAR


# ----------------------------------------------------------------------------
# Antiguedad de cartera (mes dentro del concepto + ciclo escolar)
# ----------------------------------------------------------------------------
_MESES = {
    'ENERO': 1, 'FEBRERO': 2, 'MARZO': 3, 'ABRIL': 4, 'MAYO': 5, 'JUNIO': 6,
    'JULIO': 7, 'AGOSTO': 8, 'SEPTIEMBRE': 9, 'SETIEMBRE': 9, 'OCTUBRE': 10,
    'NOVIEMBRE': 11, 'DICIEMBRE': 12,
}


def mes_del_concepto(concepto):
    """'COLEGIATURA MAYO 2025-2026' -> date(2026, 5, 1). El ciclo escolar
    agosto-julio: agosto a diciembre = primer anio; enero a julio = segundo.
    None si el concepto no trae mes/ciclo."""
    c = norm(concepto)
    mes = next((num for nombre, num in _MESES.items() if re.search(rf'\b{nombre}\b', c)), None)
    ciclo = re.search(r'(20\d{2})\s*-\s*(20\d{2})', c)
    if not mes or not ciclo:
        return None
    anio = int(ciclo.group(1)) if mes >= 8 else int(ciclo.group(2))
    return datetime.date(anio, mes, 1)


def meses_de_atraso(concepto, fecha_corte):
    fm = mes_del_concepto(concepto)
    if not fm:
        return None
    return (fecha_corte.year - fm.year) * 12 + (fecha_corte.month - fm.month)


BUCKETS_ANTIGUEDAD = [
    ('al_corriente', 'Mes en curso / futuro', lambda m: m <= 0),
    ('1', '1 mes', lambda m: m == 1),
    ('2', '2 meses', lambda m: m == 2),
    ('3', '3 meses', lambda m: m == 3),
    ('4_mas', '4 meses o más', lambda m: m >= 4),
]


def bucket_antiguedad(meses):
    if meses is None:
        return 'sin_mes', 'Sin mes en el concepto'
    for clave, etiqueta, test in BUCKETS_ANTIGUEDAD:
        if test(meses):
            return clave, etiqueta
    return 'sin_mes', 'Sin mes en el concepto'


# ----------------------------------------------------------------------------
# Parseo del 'Detalle de Pagos'
# ----------------------------------------------------------------------------
_COLUMNAS_DEFAULT = {
    'RECIBO': 0, 'MATRICULA': 1, 'NOMBRE DEL ALUMNO': 2, 'CONCEPTO': 3,
    'NIVEL': 4, 'GRADO': 5, 'GRUPO': 6, 'FECHA ABONO': 7, 'IMPORTE': 8,
    'CUENTA DEPOSITO': 9,
}
_RE_TOTAL_FINAL = re.compile(r'^(GRAN )?TOTAL:?$')


def _solo_relleno(vals):
    """True si las celdas con texto son solo puntos suspensivos ('…', '...')."""
    return all(norm(v).strip('.…') == '' for v in vals)


def _cuenta_texto(valor):
    """'0109311165' -> '0109311165'; 65509026612.0 -> '65509026612'."""
    if valor in ('', None):
        return ''
    if isinstance(valor, float):
        return str(int(valor)) if valor == int(valor) else str(valor)
    t = str(valor).strip()
    return t[:-2] if re.fullmatch(r'\d+\.0', t) else t


def _digitos(texto):
    return re.sub(r'\D', '', str(texto or ''))


def resolver_cuentas(parseo, cuentas, cuenta_defecto=None):
    """Asigna f['cuenta'] (CuentaBancaria) a cada cobro NO efectivo segun la
    columna 'Cuenta Deposito' del archivo (compara contra numero de cuenta o
    CLABE). Si no coincide usa cuenta_defecto. Devuelve lista de errores
    (cuentas del archivo que no existen en el sistema y sin cuenta por defecto)."""
    indice = {}
    for c in cuentas:
        for campo in (c.numero_cuenta, getattr(c, 'clabe', '')):
            d = _digitos(campo).lstrip('0')
            if d:
                indice.setdefault(d, c)
    sin_cuenta = Counter()
    for f in parseo['filas']:
        f['cuenta'] = None
        if es_efectivo(f['forma_pago']):
            continue
        d = _digitos(f.get('cuenta_deposito')).lstrip('0')
        cuenta = indice.get(d) if d else None
        if cuenta is None and d:
            # la CLABE contiene el numero de cuenta
            cuenta = next((c for k, c in indice.items() if len(k) > len(d) and d in k), None)
        if cuenta is None:
            cuenta = cuenta_defecto
        if cuenta is None:
            sin_cuenta[f.get('cuenta_deposito') or '(vacía)'] += 1
        f['cuenta'] = cuenta
    return [
        f"Cuenta '{k}' ({n} cobro(s)) no está registrada en Bancos: da de alta esa cuenta o elige una cuenta por defecto."
        for k, n in sin_cuenta.items()
    ]


def parsear_detalle_pagos(wb):
    """Devuelve dict con:
      filas        -> lista de cobros (dict) con su forma de pago de seccion
      omitidas     -> filas con importe <= 0 (no se importan)
      errores      -> filas ilegibles
      subtotales   -> {forma_pago: Decimal} segun el archivo
      gran_total   -> Decimal | None
      sumas        -> {forma_pago: Decimal} lo que sumaron las filas leidas
      descuadres   -> lista de textos si subtotales/gran total no cuadran
    """
    hoja = wb.sheet_by_index(0)
    cols = dict(_COLUMNAS_DEFAULT)
    filas, omitidas, errores = [], [], []
    subtotales = OrderedDict()
    sumas = defaultdict(lambda: CERO)
    gran_total = None
    forma = None

    for i in range(hoja.nrows):
        vals = [hoja.cell(i, c).value for c in range(hoja.ncols)]
        no_vacios = [v for v in vals if v not in ('', None)]
        if not no_vacios:
            continue
        primero = vals[0]
        ptxt = norm(primero) if isinstance(primero, str) else ''

        if ptxt.startswith('PAGINA'):
            continue
        if ptxt.startswith('SUB TOTAL'):
            if forma is not None:
                subtotales[forma] = _dec(no_vacios[-1])
            continue
        if _RE_TOTAL_FINAL.match(ptxt):
            gran_total = _dec(no_vacios[-1])
            continue
        if ptxt == 'RECIBO':
            for idx, v in enumerate(vals):
                if v != '' and norm(v) in cols:
                    cols[norm(v)] = idx
            continue
        if isinstance(primero, str) and ptxt and _solo_relleno(no_vacios[1:]):
            forma = primero.strip()
            continue
        if hoja.ncols < 9:
            continue

        def celda(nombre, vals=vals):
            idx = cols[nombre]
            return vals[idx] if idx < len(vals) else ''

        concepto = str(celda('CONCEPTO') or '').strip()
        importe_raw = celda('IMPORTE')
        cuenta_dep = _cuenta_texto(celda('CUENTA DEPOSITO'))
        if not concepto or importe_raw in ('', None):
            if _texto_id(celda('RECIBO')):
                errores.append(f"Fila {i + 1}: recibo {_texto_id(celda('RECIBO'))} sin concepto o importe; no se importó.")
            continue
        if forma is None:
            # El archivo nuevo no trae encabezado de seccion para el efectivo
            # (primer bloque): se identifica por la columna Cuenta Deposito.
            if norm(cuenta_dep) == 'EFECTIVO':
                forma = 'EFECTIVO'
            else:
                errores.append(f"Fila {i + 1}: no se pudo identificar la forma de pago; no se importó.")
                continue

        monto = _dec(importe_raw)
        if monto is None:
            errores.append(f"Fila {i + 1}: importe inválido ('{importe_raw}').")
            continue
        sumas[forma] += monto  # suma "bruta" para cuadrar contra el Sub Total

        fecha_raw = celda('FECHA ABONO')
        try:
            if isinstance(fecha_raw, (int, float)):
                fecha = xlrd.xldate_as_datetime(fecha_raw, wb.datemode).date()
            else:
                fecha = datetime.datetime.strptime(str(fecha_raw).strip()[:10], '%d/%m/%Y').date()  # noqa: DTZ007
        except (ValueError, TypeError):
            errores.append(f"Fila {i + 1}: fecha inválida ('{fecha_raw}').")
            continue

        fila = {
            'fila': i + 1,
            'forma_pago': forma,
            'recibo': _texto_id(celda('RECIBO')),
            'matricula': _texto_id(celda('MATRICULA')),
            'alumno': str(celda('NOMBRE DEL ALUMNO') or '').strip(),
            'concepto': concepto,
            'nivel': str(celda('NIVEL') or '').strip(),
            'grado': str(celda('GRADO') or '').strip(),
            'grupo': str(celda('GRUPO') or '').strip(),
            'cuenta_deposito': cuenta_dep,
            'fecha': fecha,
            'monto': monto,
        }
        if monto <= 0:
            omitidas.append(fila)
            continue
        filas.append(fila)

    descuadres = []
    for forma_k, sub in subtotales.items():
        if sub is not None and sumas.get(forma_k, CERO) != sub:
            descuadres.append(
                f"'{forma_k}': el archivo dice ${sub:,.2f} y las filas suman ${sumas.get(forma_k, CERO):,.2f}."
            )
    if gran_total is not None:
        suma_total = sum(sumas.values(), CERO)
        if suma_total != gran_total:
            descuadres.append(
                f"Gran Total: el archivo dice ${gran_total:,.2f} y las filas suman ${suma_total:,.2f}."
            )

    _asignar_claves(filas)
    return {
        'filas': filas, 'omitidas': omitidas, 'errores': errores,
        'subtotales': subtotales, 'gran_total': gran_total,
        'sumas': dict(sumas), 'descuadres': descuadres,
    }


def _asignar_claves(filas):
    """Huella por fila. Si el mismo cobro aparece N veces (p. ej. 3 comidas de
    $65 el mismo dia) cada repeticion lleva su numero de ocurrencia, asi
    ninguna se pierde y al re-subir el archivo ninguna se duplica."""
    contador = Counter()
    for f in filas:
        base = '|'.join([
            f['recibo'], f['matricula'], norm(f['concepto']),
            str(f['monto']), f['fecha'].isoformat(),
        ])
        contador[base] += 1
        f['clave'] = hashlib.sha1(f'{base}|{contador[base]}'.encode()).hexdigest()  # noqa: S324


# ----------------------------------------------------------------------------
# Alta de ingresos
# ----------------------------------------------------------------------------
def numero_fondeo_efectivo(fuente, anio, mes):
    return f'EFE-{fuente.upper()}-{anio}-{mes:02d}'


def importar_filas(*, empresa, usuario, fuente, archivo_nombre, cuenta_bancaria, parseo):
    """Crea el lote, los IngresoEscuela y suma el efectivo a los fondeos de
    caja chica (uno por fuente y mes, sin responsable). Debe llamarse dentro de
    transaction.atomic(). Devuelve un dict-resumen."""
    from caja_chica.models import FondeoCajaChica

    from .models import IngresoEscuela, LoteImportacionIngresos

    filas = parseo['filas']
    claves_existentes = set(
        IngresoEscuela.objects.filter(
            empresa=empresa, clave_unica__in=[f['clave'] for f in filas]
        ).values_list('clave_unica', flat=True)
    )
    nuevas = [f for f in filas if f['clave'] not in claves_existentes]
    duplicadas = len(filas) - len(nuevas)

    cuentas_lote = {f['cuenta'].pk: f['cuenta'] for f in nuevas if f.get('cuenta')}
    if len(cuentas_lote) == 1:
        cuenta_bancaria = next(iter(cuentas_lote.values()))
    elif len(cuentas_lote) > 1:
        cuenta_bancaria = None  # varias cuentas: el detalle queda en cada ingreso
    lote = LoteImportacionIngresos.objects.create(
        empresa=empresa, fuente=fuente, archivo=archivo_nombre,
        cuenta_bancaria=cuenta_bancaria, importado_por=usuario,
        filas=len(nuevas), filas_duplicadas=duplicadas,
    )

    # Fondeos de efectivo: (anio, mes) -> {total, max_fecha}
    efectivo_por_mes = defaultdict(lambda: {'total': CERO, 'max_fecha': None})
    for f in nuevas:
        if es_efectivo(f['forma_pago']):
            g = efectivo_por_mes[(f['fecha'].year, f['fecha'].month)]
            g['total'] += f['monto']
            if g['max_fecha'] is None or f['fecha'] > g['max_fecha']:
                g['max_fecha'] = f['fecha']

    fondeos = {}
    for (anio, mes), g in efectivo_por_mes.items():
        numero = numero_fondeo_efectivo(fuente, anio, mes)
        fondeo = (
            FondeoCajaChica.objects.select_for_update()
            .filter(empresa=empresa, numero_cheque=numero).first()
        )
        if fondeo is None:
            fondeo = FondeoCajaChica.objects.create(
                empresa=empresa, numero_cheque=numero,
                importe_cheque=CERO, saldo=CERO,
                fecha=datetime.date(anio, mes, 1),
                origen='cobros_efectivo', fuente=fuente,
                empleado_asignado=None, cuenta_bancaria=None,
            )
        fondeo.importe_cheque += g['total']
        fondeo.saldo += g['total']
        if g['max_fecha'] > fondeo.fecha:
            fondeo.fecha = g['max_fecha']
        fondeo.save()
        fondeos[(anio, mes)] = fondeo

    total_ef = total_bco = CERO
    objetos = []
    for f in nuevas:
        efvo = es_efectivo(f['forma_pago'])
        if efvo:
            total_ef += f['monto']
        else:
            total_bco += f['monto']
        objetos.append(IngresoEscuela(
            empresa=empresa, fecha=f['fecha'], concepto=f['concepto'],
            categoria=categoria_desde_concepto(f['concepto']),
            rubro=normalizar_rubro(f['concepto']),
            monto=f['monto'],
            forma_pago=etiqueta_forma_pago(f['forma_pago']),
            alumno=f['alumno'] or None, matricula=f['matricula'] or None,
            recibo=f['recibo'] or None, nivel=f['nivel'],
            origen='cobranza', fuente=fuente, es_efectivo=efvo,
            grado=f.get('grado', ''), grupo=f.get('grupo', ''),
            cuenta_bancaria=None if efvo else (f.get('cuenta') or cuenta_bancaria),
            fondeo=fondeos.get((f['fecha'].year, f['fecha'].month)) if efvo else None,
            lote=lote, clave_unica=f['clave'],
            importado_por=usuario, archivo_origen=archivo_nombre,
        ))
    IngresoEscuela.objects.bulk_create(objetos, batch_size=500)

    lote.total_efectivo, lote.total_banco = total_ef, total_bco
    lote.total = total_ef + total_bco
    lote.save(update_fields=['total_efectivo', 'total_banco', 'total'])
    sin_clasificar = sorted({o.concepto for o in objetos if o.rubro == RUBRO_SIN_CLASIFICAR})
    return {
        'lote': lote, 'creadas': len(nuevas), 'duplicadas': duplicadas,
        'total_efectivo': total_ef, 'total_banco': total_bco,
        'fondeos': list(fondeos.values()), 'sin_clasificar': sin_clasificar,
    }


def deshacer_lote(lote):
    """Revierte un lote: resta el efectivo de sus fondeos y borra los ingresos.
    Lanza ValueError si el fondeo ya gasto parte de ese dinero."""
    from caja_chica.models import FondeoCajaChica

    from .models import IngresoEscuela

    por_fondeo = defaultdict(lambda: CERO)
    for ing in IngresoEscuela.objects.filter(lote=lote, es_efectivo=True, fondeo__isnull=False):
        por_fondeo[ing.fondeo_id] += ing.monto

    for fondeo_id, monto in por_fondeo.items():
        fondeo = FondeoCajaChica.objects.select_for_update().get(pk=fondeo_id)
        if fondeo.saldo < monto:
            raise ValueError(
                f"No se puede deshacer: la caja chica '{fondeo.numero_cheque}' ya gastó parte de "
                f"este efectivo (saldo ${fondeo.saldo:,.2f}, el lote aportó ${monto:,.2f}). "
                "Elimina o regresa primero esos gastos/vales."
            )
    for fondeo_id, monto in por_fondeo.items():
        fondeo = FondeoCajaChica.objects.get(pk=fondeo_id)
        fondeo.importe_cheque -= monto
        fondeo.saldo -= monto
        if fondeo.importe_cheque <= 0 and not fondeo.gastocajachica_set.exists() and not fondeo.valecaja_set.exists():
            fondeo.delete()
        else:
            fondeo.save()
    lote.delete()  # CASCADE borra los IngresoEscuela del lote


def primer_y_ultimo_dia(anio, mes):
    return datetime.date(anio, mes, 1), datetime.date(anio, mes, calendar.monthrange(anio, mes)[1])
