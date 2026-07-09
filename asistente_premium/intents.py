"""Reconocimiento de intenciones mejorado"""
import re
from typing import Tuple
from .handlers import HANDLERS_REGISTRY


def recognizar_intencion(mensaje: str) -> Tuple[str, float]:
    """
    Reconoce la intención del usuario usando todos los handlers registrados.

    Estrategia:
    - Se verifica, para cada alias/keyword de cada handler, si TODAS sus
      palabras aparecen en el mensaje (sin importar orden ni palabras
      intercaladas, ej. "alta DE cliente" sí matchea "alta_cliente").
    - Si un alias hace match completo, es una señal fuerte por sí sola:
      la confianza no se penaliza por cuántos otros aliases tenga el
      handler (antes se dividía entre el total de keywords, lo que
      castigaba injustamente a los handlers con más sinónimos definidos).
    """
    mensaje_lower = mensaje.lower().strip()
    palabras_mensaje = set(re.findall(r'\w+', mensaje_lower))
    matches = {}

    for intencion, handler_class in HANDLERS_REGISTRY.items():
        keywords = [handler_class.intencion_principal] + handler_class.intencion_aliases

        for keyword in keywords:
            palabras_keyword = [p for p in keyword.split('_') if p]
            if palabras_keyword and all(p in palabras_mensaje for p in palabras_keyword):
                # Match completo de un alias -> señal fuerte de confianza máxima
                matches[intencion] = 1.0
                break  # ya no hace falta seguir revisando otros aliases de este handler

    if not matches:
        return 'otro', 0.0

    mejor_intencion = max(matches, key=matches.get)
    return mejor_intencion, matches[mejor_intencion]


def extraer_datos_mensaje(mensaje: str) -> dict:
    """Extrae datos comunes del mensaje (email, teléfono, RFC)"""
    datos = {}

    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    emails = re.findall(email_pattern, mensaje)
    if emails:
        datos['email'] = emails[0]

    telefono_pattern = r'\b(?:\+?52)?[\s.-]?(?:\d{3})?[\s.-]?\d{3}[\s.-]?\d{4}\b'
    telefonos = re.findall(telefono_pattern, mensaje)
    if telefonos:
        datos['telefono'] = telefonos[0].replace(' ', '').replace('-', '').replace('.', '')

    rfc_pattern = r'\b[A-ZÑ&]{3,4}\d{6}[A-Z0-9]{3}\b'
    rfcs = re.findall(rfc_pattern, mensaje)
    if rfcs:
        datos['rfc'] = rfcs[0]

    # Folio de factura, ej. "factura ABC123" o "factura F-2026-045"
    # (usado para precargar el campo 'folio' cuando el botón "Asignar pago"
    # manda un mensaje tipo "Quiero asignar un pago a la factura ABC123")
    folio_match = re.search(r'factura\s+([A-Za-z0-9\-_/]+)', mensaje, re.IGNORECASE)
    if folio_match:
        datos['folio'] = folio_match.group(1)

    return datos