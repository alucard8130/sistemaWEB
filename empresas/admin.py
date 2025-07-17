from django.contrib import admin
from .models import Empresa

# Register your models here.

@admin.register(Empresa)
class EmpresaAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'rfc', 'cuenta_bancaria', 'numero_cuenta', 'saldo_inicial', 'saldo_final')
    search_fields = ('nombre', 'rfc')
