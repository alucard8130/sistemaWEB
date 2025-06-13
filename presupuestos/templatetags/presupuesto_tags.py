# presupuestos/templatetags/presupuesto_tags.py

from django import template
register = template.Library()

@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)

@register.simple_tag
def get_presupuesto(presup_dict, tipo_id, mes):
    """
    Obtiene el objeto presupuesto a partir del dict y la tupla (tipo_id, mes).
    Uso: {% get_presupuesto presup_dict tipo.id mes as presup %}
    """
    return presup_dict.get((tipo_id, mes), None)