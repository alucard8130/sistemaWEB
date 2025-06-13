from django import template

register = template.Library()

#@register.filter
#def get_item(dictionary, key):
 #   return dictionary.get(key)

#@register.filter
#def get_item(dictionary, key):
 #   if dictionary is None:
  #      return None
   # return dictionary.get(key)

@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)

#@register.filter
#def get_tuple_item(dictionary, key_tuple):
 #   if dictionary is None or key_tuple is None:
  #      return None
   # try:
    #    a, b = key_tuple.split(',')
     #   return dictionary.get((int(a), int(b)))
   # except Exception:
    #    return None
    
@register.filter
def get_tuple_item(dictionary, key_tupla):
    """Permite acceder a un dict con clave tipo tupla, separando los argumentos por coma."""
    if not dictionary or not key_tupla:
        return None
     #Si el key ya viene como tupla
    if isinstance(key_tupla, (tuple, list)):
        return dictionary.get(tuple(key_tupla))
     #Si viene como string: "12,6"
    if isinstance(key_tupla, str):
        partes = [int(x.strip()) for x in key_tupla.split(',')]
        return dictionary.get(tuple(partes))
    return None

@register.filter
def get_tuple(d, args):
    """Permite d|get_tuple:'id,mes'."""
    if not d or not args:
        return None
    id_str, mes_str = args.split(',')
    key = (int(id_str), int(mes_str))
    return d.get(key)