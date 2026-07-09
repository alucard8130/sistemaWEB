"""Utilidades para el control de asistencia"""
import math


def calcular_distancia_metros(lat1, lng1, lat2, lng2):
    """
    Distancia en metros entre dos coordenadas GPS, usando la fórmula
    haversine (suficientemente precisa para validar cercanía a una oficina;
    no se necesita nada más sofisticado para este caso de uso).
    """
    radio_tierra_m = 6371000
    phi1, phi2 = math.radians(float(lat1)), math.radians(float(lat2))
    dphi = math.radians(float(lat2) - float(lat1))
    dlambda = math.radians(float(lng2) - float(lng1))

    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * radio_tierra_m * math.asin(math.sqrt(a))