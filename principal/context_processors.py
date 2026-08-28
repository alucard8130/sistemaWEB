# ============================================================
# Colocalo en: cualquier_app/context_processors.py (puede ser el
# mismo archivo donde ya tengas otros context processors)
#
# Y registralo en settings.py, dentro de TEMPLATES -> OPTIONS ->
# context_processors (agrega esta linea a la lista que ya tienes):
#
#     'tu_app.context_processors.stripe_context',
# ============================================================

from django.conf import settings


def stripe_context(request):
    """Hace disponible STRIPE_PUBLIC_KEY en TODAS las plantillas,
    sin que cada vista tenga que pasarla a mano -- necesario para
    los botones de pago con tarjeta que viven en el navbar (que
    aparece en todas las pantallas, no solo en dashboard_inicio)."""
    return {
        'STRIPE_PUBLIC_KEY': settings.STRIPE_PUBLIC_KEY,
    }