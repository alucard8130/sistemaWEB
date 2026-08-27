from django.apps import AppConfig


class EmpresasConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'empresas'

    def ready(self):
        import acceso_empresas.signals  # noqa: F401
        import empresas.signals  # Asegúrate de importar el módulo de señales para registrar los handlers  # noqa: F401
