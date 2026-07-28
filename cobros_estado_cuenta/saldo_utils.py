from decimal import Decimal
from django.db.models import Sum


from facturacion.models import CobroOtrosIngresos, Pago
from gastos.models import PagoGasto



# def calcular_saldo_cuenta(cuenta):
#     """
#     Saldo aproximado de una cuenta bancaria, calculado a partir de todo lo
#     que ha pasado por GESAC. No refleja movimientos bancarios que nunca se
#     hayan capturado en el sistema.
#     """
# # ajusta rutas

#     saldo = cuenta.saldo_inicial or Decimal('0')

#     total_pagos = Pago.objects.filter(cuenta_bancaria=cuenta).aggregate(t=Sum('monto'))['t'] or Decimal('0')
#     total_cobros_otros = CobroOtrosIngresos.objects.filter(cuenta_bancaria=cuenta).aggregate(t=Sum('monto'))['t'] or Decimal('0')
#     total_pagos_gasto = PagoGasto.objects.filter(cuenta_bancaria=cuenta).aggregate(t=Sum('monto'))['t'] or Decimal('0')

#     total_traspasos_salientes = TraspasoCuenta.objects.filter(cuenta_origen=cuenta).aggregate(t=Sum('monto'))['t'] or Decimal('0')
#     total_traspasos_entrantes = TraspasoCuenta.objects.filter(cuenta_destino=cuenta).aggregate(t=Sum('monto'))['t'] or Decimal('0')

#     saldo += total_pagos
#     saldo += total_cobros_otros
#     saldo -= total_pagos_gasto
#     saldo -= total_traspasos_salientes
#     saldo += total_traspasos_entrantes

#     return saldo