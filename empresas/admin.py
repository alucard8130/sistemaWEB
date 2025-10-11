from django.contrib import admin
from .models import Empresa

# Register your models here.

@admin.register(Empresa)
class EmpresaAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'rfc', 'regimen_fiscal', 'cuenta_bancaria', 'numero_cuenta', 'saldo_inicial', 'saldo_final','stripe_public_key', 'stripe_secret_key', 'stripe_webhook_secret')
    search_fields = ('nombre', 'rfc')
