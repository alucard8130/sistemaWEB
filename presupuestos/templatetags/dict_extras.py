from django import template

register = template.Library()

""" @register.filter
def get_item(dictionary, key):
    # Si la clave llega como string "1,2", convíertela en tupla de int
    if isinstance(key, str) and ',' in key:
        parts = key.split(',')
        try:
            key = (int(parts[0]), int(parts[1]))
        except Exception:
            pass
    return dictionary.get(key)"""
"""@register.filter
def get_item(dictionary, key):
    # key debe venir como una tupla
    if not dictionary:
        return None
    if isinstance(key, str) and ',' in key:
        k1, k2 = key.split(',')
        key = (int(k1.strip()), int(k2.strip()))
    return dictionary.get(key)"""

"""@register.filter
def get_item(dictionary, key):
    
    return dictionary.get(key)"""

"""@register.filter
def get_item(dictionary, key):
    if not dictionary:
        return None
    # Acepta clave como "12,3" y la convierte a tupla
    if isinstance(key, str) and ',' in key:
        try:
            k1, k2 = key.split(',')
            key = (int(k1.strip()), int(k2.strip()))
        except Exception:
            return None
    return dictionary.get(key)"""
"""@register.filter
def get_item(dictionary, key):
    
    
    if not dictionary or not key:
        return None
    if isinstance(key, str):
        if '-' in key:
            k1, k2 = key.split('-')
            key = (int(k1), int(k2))
        elif ',' in key:
            k1, k2 = key.split(',')
            key = (int(k1), int(k2))
    return dictionary.get(key)"""
#@register.filter
#def get_item(dictionary, key):
 #   return dictionary.get(key)
#@register.filter
#def get_item(dictionary, key):
    # Si la clave es string tipo "1,5", conviértela en tupla
 #   if isinstance(key, str) and ',' in key:
  #      key = tuple(int(k) for k in key.split(','))
   # return dictionary.get(key)

@register.filter
def get_tuple_item(d, args):
    """Uso: {{ mydict|get_tuple_item:"id,mes" }}"""
    try:
        k1, k2 = args.split(',')
        return d.get((int(k1), int(k2)))
    except Exception:
        return None
    
@register.filter
def get_tuple(d, args):
    """Permite d|get_tuple:'id,mes'."""
    if not d or not args:
        return None
    id_str, mes_str = args.split(',')
    key = (int(id_str), int(mes_str))
    return d.get(key)

"""@register.filter
def get_presupuesto(d, key):
    
    try:
        tipoid, mes = key.split(',')
        return d.get((int(tipoid), int(mes)))
    except Exception:
        return None"""
    
@register.simple_tag
def get_presupuesto(presup_dict, tipo_id, mes):
    return presup_dict.get((tipo_id, mes))    

@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)

@register.filter
def dict_index(d, k):
    try:
        return d[k]
    except Exception:
        return None

@register.filter
def dict_index_nested(d, key):
    """Devuelve el valor de la siguiente clave, usado para dicts anidados."""
    if d is None:
        return None
    return d.get(key, {})

@register.filter
def sum_list(lst):
    return sum(lst) if lst else 0

"""@register.filter
def sum_list(iterable):
    #Suma los valores de una lista (ignora None y cadenas)
    if iterable is None:
        return 0
    try:
        return sum([x or 0 for x in iterable if isinstance(x, (int, float))])
    except Exception:
        # Si iterable es un dict, suma los valores numéricos
        if isinstance(iterable, dict):
            return sum([v or 0 for v in iterable.values() if isinstance(v, (int, float))])
        return 0 """
    
@register.filter
def dict_key(d, key):
    return d.get(key)   
 
@register.filter
def list_index(l, i):
    try:
        return l[i-1]  # OJO: si tu forloop.counter0, usa simplemente l[i]
    except Exception:
        return 0