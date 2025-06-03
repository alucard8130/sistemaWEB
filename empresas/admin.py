from django.contrib import admin
from .models import Empresa

# Register your models here.

@admin.register(Empresa)
class EmpresaAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'rfc', 'email', 'telefono')
    search_fields = ('nombre', 'rfc')
