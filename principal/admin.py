
from django.contrib import admin

from areas.models import AreaComun
from locales.models import LocalComercial
from .models import PerfilUsuario
from .models import VisitanteAcceso
from django.contrib.auth.hashers import make_password
from django import forms

# Register your models here.
@admin.register(PerfilUsuario)
class PerfilUsuarioAdmin(admin.ModelAdmin):
    list_display = ['usuario', 'empresa']
    search_fields = ['usuario__username', 'empresa__nombre']

class VisitanteAccesoForm(forms.ModelForm):
    class Meta:
        model = VisitanteAcceso
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Si hay empresas seleccionadas, filtra locales y áreas por esas empresas
        empresas = self.data.getlist('empresas') if self.data else []
        if empresas:
            self.fields['locales'].queryset = LocalComercial.objects.filter(empresa_id__in=empresas)
            self.fields['areas'].queryset = AreaComun.objects.filter(empresa_id__in=empresas)
        elif self.instance.pk and self.instance.empresas.exists():
            empresas_ids = self.instance.empresas.values_list('id', flat=True)
            self.fields['locales'].queryset = LocalComercial.objects.filter(empresa_id__in=empresas_ids)
            self.fields['areas'].queryset = AreaComun.objects.filter(empresa_id__in=empresas_ids)
        else:
            self.fields['locales'].queryset = LocalComercial.objects.none()
            self.fields['areas'].queryset = AreaComun.objects.none()
        # if 'empresa' in self.data:
        #     try:
        #         empresa_id = int(self.data.get('empresa'))
        #         self.fields['locales'].queryset = LocalComercial.objects.filter(empresa_id=empresa_id)
        #         self.fields['areas'].queryset = AreaComun.objects.filter(empresa_id=empresa_id)
        #     except (ValueError, TypeError):
        #         pass
        # elif self.instance.pk:
        #     empresa = self.instance.empresa
        #     self.fields['locales'].queryset = LocalComercial.objects.filter(empresa=empresa)
        #     self.fields['areas'].queryset = AreaComun.objects.filter(empresa=empresa)
        # else:
        #     self.fields['locales'].queryset = LocalComercial.objects.none()
        #     self.fields['areas'].queryset = AreaComun.objects.none()

class VisitanteAccesoAdmin(admin.ModelAdmin):
    form = VisitanteAccesoForm
    list_display = ('username', 'get_empresas', 'acceso_api_reporte', 'get_locales', 'get_areas', 'es_admin')
    search_fields = ('username', 'empresas__nombre', 'locales__numero', 'areas__nombre', 'es_admin')
    list_filter = ('empresas', 'locales', 'areas', 'es_admin')
    fields = ('username', 'password', 'es_admin', 'empresas', 'acceso_api_reporte', 'locales', 'areas')
    filter_horizontal = ('empresas', 'locales', 'areas')
    # list_display = ('username', 'empresa','acceso_api_reporte', 'get_locales', 'get_areas', 'es_admin')
    # search_fields = ('username', 'empresa__nombre', 'locales__numero', 'areas__nombre', 'es_admin')
    # list_filter = ('empresa', 'locales', 'areas', 'es_admin')
    # fields = ('username', 'password', 'es_admin','empresa','acceso_api_reporte', 'locales', 'areas')
    # filter_horizontal = ('locales', 'areas')

    def get_empresas(self, obj):
        return ", ".join([str(e) for e in obj.empresas.all()])
    get_empresas.short_description = "Empresas"
    
    def get_locales(self, obj):
        return ", ".join([str(l) for l in obj.locales.all()])
    get_locales.short_description = "Locales"

    def get_areas(self, obj):
        return ", ".join([str(a) for a in obj.areas.all()])
    get_areas.short_description = "Áreas comunes"

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        form.base_fields['password'].widget = admin.widgets.AdminTextInputWidget()
        form.base_fields['password'].help_text = "Escribe la contraseña en texto plano. Se guardará encriptada."
        return form

    def save_model(self, request, obj, form, change):
        raw_password = form.cleaned_data.get('password')
        if raw_password and (not change or not obj.check_password(raw_password)):
            from django.contrib.auth.hashers import make_password
            obj.password = make_password(raw_password)
        super().save_model(request, obj, form, change)

admin.site.register(VisitanteAcceso, VisitanteAccesoAdmin)