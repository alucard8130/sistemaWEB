from datetime import date
from django.shortcuts import render
from .models import Factura

def debe_mostrar_recordatorio_facturacion(empresa):
    hoy = date.today()
    if hoy.day > 10 and empresa:
        existe = Factura.objects.filter(
            empresa=empresa,
            fecha_emision__year=hoy.year,
            fecha_emision__month=hoy.month
        ).exists()
        return not existe
    return False
