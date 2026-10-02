from django import template

register = template.Library()


@register.filter
def get_item(diccionario, clave):
    """Permite hacer diccionario[clave] en el template, cuando la
    clave es una variable (no un literal) -- Django no lo soporta
    directo con la sintaxis de punto."""
    if diccionario is None:
        return None
    return diccionario.get(clave)


@register.filter
def sub(valor_a, valor_b):
    """Resta simple para el template -- Django no trae un filtro de
    resta por default."""
    try:
        return valor_a - valor_b
    except TypeError:
        return 0

@register.filter
def index(lista, i):
    """Permite hacer lista[i] en el template, cuando i es una variable
    (el contador del forloop, por ejemplo)."""
    try:
        return lista[i]
    except (IndexError, TypeError):
        return None    