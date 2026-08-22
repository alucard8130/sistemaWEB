
import datetime
import re
import xml.etree.ElementTree as ET
from decimal import Decimal, InvalidOperation

#============================================================
# nomina/utils.py -- reemplaza tu funcion parsear_xml_nomina()
# completa por esta version. Se conservan los mismos totales de
# siempre, y se agrega la lista "conceptos" con el detalle linea
# por linea de percepciones, deducciones, y otros pagos.
# ============================================================


NS = {
    "cfdi": "http://www.sat.gob.mx/cfd/4",
    "nomina12": "http://www.sat.gob.mx/nomina12",
    "tfd": "http://www.sat.gob.mx/TimbreFiscalDigital",
}

# NUEVO -- patrón estándar de UUID (el mismo formato que usa el SAT para
# el folio fiscal). Se valida ANTES de tocar la base de datos, para que
# un XML manipulado o corrupto se marque como "error" de forma limpia,
# en vez de tronar con un error de base de datos a media transacción.
_PATRON_UUID = re.compile(
    r"^[0-9A-Fa-f]{8}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{12}$"
)


class XMLNominaInvalido(Exception):
    pass


def _to_decimal(valor):
    if valor is None or valor == "":
        return Decimal("0")
    try:
        return Decimal(str(valor))
    except InvalidOperation:
        return Decimal("0")


def _to_date(valor):
    if not valor:
        return None
    try:
        return datetime.date.fromisoformat(valor[:10])
    except ValueError:
        return None


def parsear_xml_nomina(contenido_xml):
    """
    Parsea un CFDI de Nomina 1.2 y regresa un diccionario con los datos
    del receptor, los totales (igual que antes), y AHORA TAMBIEN la
    lista completa de conceptos individuales (percepciones, deducciones,
    y otros pagos), tal como vienen desglosados en el XML.
    """
    try:
        root = ET.fromstring(contenido_xml)
    except ET.ParseError as e:
        raise XMLNominaInvalido(f"El archivo no es un XML valido: {e}")

    receptor = root.find("cfdi:Receptor", NS)
    if receptor is None:
        raise XMLNominaInvalido("El XML no tiene un nodo cfdi:Receptor -- no parece ser un CFDI valido.")

    rfc_receptor = receptor.get("Rfc")
    nombre_receptor = receptor.get("Nombre")
    if not rfc_receptor:
        raise XMLNominaInvalido("El XML no trae el RFC del receptor.")

    complemento = root.find("cfdi:Complemento", NS)
    if complemento is None:
        raise XMLNominaInvalido("El XML no tiene complemento -- no parece ser un CFDI de Nomina.")

    nomina = complemento.find("nomina12:Nomina", NS)
    if nomina is None:
        raise XMLNominaInvalido("El XML no tiene el complemento de Nomina (nomina12:Nomina).")

    fecha_pago = _to_date(nomina.get("FechaPago"))
    periodo_inicio = _to_date(nomina.get("FechaInicialPago"))
    periodo_fin = _to_date(nomina.get("FechaFinalPago"))
    total_percepciones = _to_decimal(nomina.get("TotalPercepciones"))
    total_deducciones = _to_decimal(nomina.get("TotalDeducciones"))
    total_otros_pagos = _to_decimal(nomina.get("TotalOtrosPagos"))
    neto_pagado = total_percepciones + total_otros_pagos - total_deducciones

    # ---- NUEVO: detalle concepto por concepto ----
    conceptos = []

    nodo_percepciones = nomina.find("nomina12:Percepciones", NS)
    if nodo_percepciones is not None:
        for p in nodo_percepciones.findall("nomina12:Percepcion", NS):
            gravado = _to_decimal(p.get("ImporteGravado"))
            exento = _to_decimal(p.get("ImporteExento"))
            conceptos.append({
                "tipo": "percepcion",
                "clave": p.get("Clave") or p.get("TipoPercepcion"),
                "concepto": (p.get("Concepto") or "Percepcion sin nombre").strip(),
                "importe_gravado": gravado,
                "importe_exento": exento,
            })

    nodo_deducciones = nomina.find("nomina12:Deducciones", NS)
    if nodo_deducciones is not None:
        for d in nodo_deducciones.findall("nomina12:Deduccion", NS):
            conceptos.append({
                "tipo": "deduccion",
                "clave": d.get("Clave") or d.get("TipoDeduccion"),
                "concepto": (d.get("Concepto") or "Deduccion sin nombre").strip(),
                "importe_gravado": _to_decimal(d.get("Importe")),
                "importe_exento": Decimal("0"),
            })

    nodo_otros_pagos = nomina.find("nomina12:OtrosPagos", NS)
    if nodo_otros_pagos is not None:
        for o in nodo_otros_pagos.findall("nomina12:OtroPago", NS):
            conceptos.append({
                "tipo": "otro_pago",
                "clave": o.get("Clave") or o.get("TipoOtroPago"),
                "concepto": (o.get("Concepto") or "Otro pago sin nombre").strip(),
                "importe_gravado": _to_decimal(o.get("Importe")),
                "importe_exento": Decimal("0"),
            })

    tfd = complemento.find("tfd:TimbreFiscalDigital", NS)
    uuid_fiscal = tfd.get("UUID") if tfd is not None else None
    if not uuid_fiscal:
        raise XMLNominaInvalido("El XML no esta timbrado -- no tiene UUID fiscal (TimbreFiscalDigital).")
    if not _PATRON_UUID.match(uuid_fiscal.strip()):
        raise XMLNominaInvalido(
            f"El folio fiscal (UUID) del XML no tiene un formato valido -- "
            f"parece corrupto o manipulado: \"{uuid_fiscal[:60]}\""
        )

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
        "conceptos": conceptos,
    }


