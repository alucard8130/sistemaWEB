
import re
import unicodedata
 
 
# ============================================================
# Helper -- colócalo arriba del archivo (junto a tus otros
# helpers/imports), fuera de la función.
# ============================================================
def normalizar_nombre_empresa(nombre):
    """
    Normaliza un nombre de escuela para comparar aunque venga con
    mayúsculas distintas, acentos distintos, espacios de más, o
    sufijos legales comunes -- para detectar que 'Liceo Real del
    Valle' y 'liceo  real del valle A.C.' son la misma escuela.
    """
    if not nombre:
        return ""
 
    texto = nombre.strip().lower()
    texto = unicodedata.normalize('NFKD', texto)
    texto = ''.join(c for c in texto if not unicodedata.combining(c))
 
    for sufijo in [' a.c.', ' a c', ' s.c.', ' s c', ' s.a. de c.v.', ' sa de cv']:
        if texto.endswith(sufijo):  # noqa: FURB188
            texto = texto[: -len(sufijo)]
 
    texto = re.sub(r'[^\w\s]', '', texto)
    texto = re.sub(r'\s+', ' ', texto).strip()
    return texto