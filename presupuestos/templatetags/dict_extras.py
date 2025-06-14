from django import template

register = template.Library()


@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)

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

@register.filter
def get_presupuesto(d, key):
    """key debe ser 'tipoid,mes' como string"""
    try:
        tipoid, mes = key.split(',')
        return d.get((int(tipoid), int(mes)))
    except Exception:
        return None