from django import template

register = template.Library()

#@register.filter
#def get_item(dictionary, key):
 #   return dictionary.get(key)

@register.filter
def get_item(dictionary, key):
    if dictionary is None:
        return None
    return dictionary.get(key)

@register.filter
def get_tuple_item(dictionary, key):
    if dictionary is None or key is None:
        return None
    try:
        a, b = key.split(',')
        return dictionary.get((int(a), int(b)))
    except Exception:
        return None
    
#@register.filter
#def get_tuple_item(dictionary, key):
    """Permite acceder a un dict con clave tipo tupla, separando los argumentos por coma."""
 #   if not dictionary or not key:
  #      return None
    # Si el key ya viene como tupla
   # if isinstance(key, (tuple, list)):
    #    return dictionary.get(tuple(key))
    # Si viene como string: "12,6"
   # if isinstance(key, str):
    #    partes = [int(x.strip()) for x in key.split(',')]
     #   return dictionary.get(tuple(partes))
    #return None
