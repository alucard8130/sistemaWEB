import random
import re
import string


def generar_referencia_pago_propiedad(cliente_id, tipo, numero):
    """
    Genera una referencia de pago única para una propiedad (local o área común).
    Formato: RF-{cliente_id 5 dígitos}-{tipo}{numero saneado, máx 8}-{sufijo aleatorio 4}
    tipo: 'L' para LocalComercial, 'A' para AreaComun
    Ejemplo: RF-00042-LD02-X7K3
    """
    numero_saneado = re.sub(r'[^A-Za-z0-9]', '', numero or '').upper()[:8]
    sufijo = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
    return f"RF-{cliente_id:05d}-{tipo}{numero_saneado}-{sufijo}"


def generar_referencia_corta():
    """Referencia de pago corta: 7 dígitos numéricos (cabe en el campo "Referencia numérica" de SPEI).
    Única entre locales, áreas comunes y grupos de facturación. Nunca empieza con 0."""
    from areas.models import AreaComun
    from facturacion.models import GrupoFacturacion
    from locales.models import LocalComercial

    for _ in range(50):
        ref = str(random.randint(1000000, 9999999))
        if not (
            LocalComercial.objects.filter(referencia_corta=ref).exists()
            or AreaComun.objects.filter(referencia_corta=ref).exists()
            or GrupoFacturacion.objects.filter(referencia_corta=ref).exists()
        ):
            return ref
    raise ValueError("No fue posible generar una referencia corta única.")
