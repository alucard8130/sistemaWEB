
import datetime
import xml.etree.ElementTree as ET
from decimal import Decimal, InvalidOperation

# ============================================================#
# Parsea un XML de CFDI con Complemento de Nómina (1.2), y regresa
# un diccionario con los datos que necesitamos. No calcula nada,
# no valida el sello fiscal -- solo LEE lo que ya viene timbrado.
# ============================================================


NS = {
    "cfdi": "http://www.sat.gob.mx/cfd/4",
    "nomina12": "http://www.sat.gob.mx/nomina12",
    "tfd": "http://www.sat.gob.mx/TimbreFiscalDigital",
}


class XMLNominaInvalido(Exception):
    pass


def _to_decimal(valor):
    if valor is None:
        return Decimal("0")
    try:
        return Decimal(str(valor))
    except InvalidOperation:
        return Decimal("0")


def _to_date(valor):
    if not valor:
        return None
    try:
        # Los XML de nómina traen fechas como "2026-08-15" o con hora "2026-08-15T00:00:00"
        return datetime.date.fromisoformat(valor[:10])
    except ValueError:
        return None


def parsear_xml_nomina(archivo_bytes):
    """
    archivo_bytes: contenido crudo del archivo XML subido.
    Regresa un dict con: uuid_fiscal, rfc_receptor, nombre_receptor,
    fecha_pago, periodo_inicio, periodo_fin, total_percepciones,
    total_deducciones, neto_pagado.

    Lanza XMLNominaInvalido si el archivo no es un CFDI de nómina válido
    (por ejemplo, si le suben un XML de otro tipo, o un archivo corrupto).
    """
    try:
        root = ET.fromstring(archivo_bytes)
    except ET.ParseError as e:
        raise XMLNominaInvalido(f"El archivo no es un XML válido: {e}")

    # --- Receptor (el empleado) ---
    receptor = root.find("cfdi:Receptor", NS)
    if receptor is None:
        raise XMLNominaInvalido("No se encontró el nodo Receptor en el CFDI.")

    rfc_receptor = receptor.get("Rfc")
    nombre_receptor = receptor.get("Nombre")

    # --- Complemento de Nómina ---
    complemento = root.find("cfdi:Complemento", NS)
    if complemento is None:
        raise XMLNominaInvalido("Este XML no trae Complemento -- no parece ser un CFDI de nómina.")

    nomina = complemento.find("nomina12:Nomina", NS)
    if nomina is None:
        raise XMLNominaInvalido("No se encontró el Complemento de Nómina (nomina12:Nomina) en este XML.")

    fecha_pago = _to_date(nomina.get("FechaPago"))
    periodo_inicio = _to_date(nomina.get("FechaInicialPago"))
    periodo_fin = _to_date(nomina.get("FechaFinalPago"))
    total_percepciones = _to_decimal(nomina.get("TotalPercepciones"))
    total_deducciones = _to_decimal(nomina.get("TotalDeducciones"))
    # NUEVO -- "Otros Pagos" (ej. Subsidio para el Empleo) SÍ se le entrega
    # al trabajador, aunque no sea una "percepción" fiscalmente -- hay que
    # sumarlo también, o el neto sale por debajo de lo realmente depositado.
    total_otros_pagos = _to_decimal(nomina.get("TotalOtrosPagos"))

    # El neto realmente pagado -- percepciones + otros pagos, menos deducciones.
    neto_pagado = total_percepciones + total_otros_pagos - total_deducciones

    # --- Folio fiscal (UUID) -- para detectar duplicados ---
    tfd = complemento.find("tfd:TimbreFiscalDigital", NS)
    uuid_fiscal = tfd.get("UUID") if tfd is not None else None

    if not rfc_receptor:
        raise XMLNominaInvalido("El XML no trae RFC del receptor.")

    return {
        "uuid_fiscal": uuid_fiscal,
        "rfc_receptor": rfc_receptor.strip().upper(),
        "nombre_receptor": (nombre_receptor or "").strip(),
        "fecha_pago": fecha_pago,
        "periodo_inicio": periodo_inicio,
        "periodo_fin": periodo_fin,
        "total_percepciones": total_percepciones,
        "total_deducciones": total_deducciones,
        "total_otros_pagos": total_otros_pagos,
        "neto_pagado": neto_pagado,
    }