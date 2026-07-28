from django.apps import AppConfig




class AccesoEmpresasConfig(AppConfig):  # ajusta al nombre real de tu clase
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'acceso_empresas'  # ajusta al app_label real

    def ready(self):
        import acceso_empresas.signals  # ajusta el import real