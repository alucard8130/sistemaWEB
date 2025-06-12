import os
from django import template
from django.conf import settings

register = template.Library()

@register.filter
def archivo_existe(filefield):
    if not filefield:
        return False
    path = os.path.join(settings.MEDIA_ROOT, str(filefield))
    return os.path.isfile(path)