

from functools import lru_cache
from pathlib import Path

from django.conf import settings

# Ajusta esta ruta a donde guardes el archivo manual_gesac_sherlock.md
# dentro de tu proyecto (ej. junto a otros archivos estáticos/de datos).
RUTA_MANUAL = Path(settings.BASE_DIR) / "asistente_premium" / "static" / "manual_gesac_sherlock.md"


@lru_cache(maxsize=1)
def cargar_manual_gesac() -> str:
    """
    Carga el manual completo UNA sola vez por proceso (cacheado en memoria
    con lru_cache) -- no se vuelve a leer del disco en cada mensaje.

    Si actualizas el archivo .md y necesitas que el cambio se refleje sin
    reiniciar el servidor, puedes llamar a cargar_manual_gesac.cache_clear()
    desde una vista de administración, o simplemente reiniciar el proceso
    (lo normal en un deploy).
    """
    try:
        return RUTA_MANUAL.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""