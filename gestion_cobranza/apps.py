from django.apps import AppConfig


class GestionCobranzaConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'gestion_cobranza'


    def ready(self):
        import gestion_cobranza.signals  # noqa: F401
