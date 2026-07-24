import random
import string
import re


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