from django.contrib import admin
from .models import Empresa, CuentaBancaria

# Register your models here.

@admin.register(Empresa)
class EmpresaAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'rfc', 'regimen_fiscal', 'stripe_public_key', 'stripe_secret_key', 'stripe_webhook_secret')
    search_fields = ('nombre', 'rfc')


@admin.register(CuentaBancaria)
class CuentaBancariaAdmin(admin.ModelAdmin):
    list_display = ('empresa', 'banco', 'numero_cuenta', 'tipo_cuenta', 'moneda', 'saldo_inicial', 'saldo_final', 'activa')
    list_filter = ('banco', 'tipo_cuenta', 'moneda', 'activa')
    search_fields = ('numero_cuenta', 'clabe', 'empresa__nombre')