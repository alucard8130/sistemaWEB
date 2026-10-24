import os

from django import template
from django.conf import settings
from django.core.files.storage import FileSystemStorage, default_storage

register = template.Library()


@register.filter
def archivo_existe(filefield):
    if not filefield:
        return False
    # En almacenamiento remoto (Spaces/S3) no se consulta archivo por archivo: se asume que existe.
    if not isinstance(default_storage, FileSystemStorage):
        return True
    path = os.path.join(settings.MEDIA_ROOT, str(filefield))
    return os.path.isfile(path)
