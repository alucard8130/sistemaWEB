
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
        if 'empresa' in self.data:
            try:
                empresa_id = int(self.data.get('empresa'))
                self.fields['locales'].queryset = LocalComercial.objects.filter(empresa_id=empresa_id)
                self.fields['areas'].queryset = AreaComun.objects.filter(empresa_id=empresa_id)
            except (ValueError, TypeError):
                pass
        elif self.instance.pk:
            empresa = self.instance.empresa
            self.fields['locales'].queryset = LocalComercial.objects.filter(empresa=empresa)
            self.fields['areas'].queryset = AreaComun.objects.filter(empresa=empresa)
        else:
            self.fields['locales'].queryset = LocalComercial.objects.none()
            self.fields['areas'].queryset = AreaComun.objects.none()

class VisitanteAccesoAdmin(admin.ModelAdmin):
    form = VisitanteAccesoForm
    list_display = ('username', 'empresa', 'get_locales', 'get_areas')
    search_fields = ('username', 'empresa__nombre', 'locales__numero', 'areas__nombre')
    list_filter = ('empresa', 'locales', 'areas')
    fields = ('username', 'password', 'empresa', 'locales', 'areas')
    filter_horizontal = ('locales', 'areas')

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